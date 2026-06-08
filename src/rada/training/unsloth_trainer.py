"""Unsloth LoRA trainer wrapper for reflection/policy updates."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rada.models.resolver import resolve_model_path
from rada.training.adapter_export import (
    AdapterArtifact,
    adapter_output_dir,
    write_lora_config,
    write_stub_adapter_files,
    write_training_manifest,
)
from rada.training.config import TrainingConfig
from rada.training.dataset import ChatExample, examples_to_sft_rows

if TYPE_CHECKING:
    from datasets import Dataset

logger = logging.getLogger(__name__)


class StubTrainer:
    """CI-friendly trainer that emits adapter artifacts without GPU deps."""

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    def train(self, examples: list[ChatExample]) -> AdapterArtifact:
        adapter_dir = adapter_output_dir(self.config)
        return write_stub_adapter_files(
            adapter_dir,
            config=self.config,
            row_count=len(examples),
        )


class UnslothTrainer:
    """Wraps Unsloth FastLanguageModel for LoRA SFT on feedback examples."""

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    def train(self, examples: list[ChatExample]) -> AdapterArtifact:
        if not examples:
            msg = "training requires at least one example"
            raise ValueError(msg)

        try:
            from unsloth import FastLanguageModel  # type: ignore[import-untyped]
            from trl import SFTTrainer
            from transformers import TrainingArguments
            from datasets import Dataset
        except ImportError as exc:
            msg = "unsloth backend requires pip install -e '.[unsloth]'"
            raise ImportError(msg) from exc

        base_path = resolve_model_path(self.config.model_id)
        adapter_dir = adapter_output_dir(self.config)
        adapter_dir.mkdir(parents=True, exist_ok=True)

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(base_path),
            max_seq_length=self.config.max_seq_length,
            dtype=None,
            load_in_4bit=True,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=self.config.lora.rank,
            target_modules=self.config.lora.target_modules,
            lora_alpha=self.config.lora.alpha,
            lora_dropout=self.config.lora.dropout,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=42,
        )

        rows = examples_to_sft_rows(examples)
        dataset: Dataset = Dataset.from_list(rows)

        training_args = TrainingArguments(
            output_dir=str(adapter_dir / "checkpoints"),
            per_device_train_batch_size=self.config.batch_size,
            num_train_epochs=self.config.epochs,
            learning_rate=self.config.learning_rate,
            logging_steps=1,
            save_strategy="steps",
            save_steps=self.config.checkpoint_interval,
            save_total_limit=self.config.checkpoint_keep_last,
            resume_from_checkpoint=self.config.resume_from,
            report_to="none",
        )

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            dataset_text_field="text",
            max_seq_length=self.config.max_seq_length,
            args=training_args,
        )
        trainer.train()

        model.save_pretrained(str(adapter_dir))
        tokenizer.save_pretrained(str(adapter_dir))

        adapter_id = f"{self.config.model_id}-{self.config.output_run_id}"
        manifest_path = write_training_manifest(
            adapter_dir,
            config=self.config,
            adapter_id=adapter_id,
            row_count=len(examples),
            extra={"base_model_path": str(base_path)},
        )
        lora_config_path = write_lora_config(adapter_dir, config=self.config)

        logger.info("saved adapter to %s", adapter_dir)
        return AdapterArtifact(
            run_id=self.config.output_run_id,
            model_id=self.config.model_id,
            adapter_path=adapter_dir,
            manifest_path=manifest_path,
            lora_config_path=lora_config_path,
        )


def build_trainer(config: TrainingConfig) -> StubTrainer | UnslothTrainer:
    if config.backend == "stub":
        return StubTrainer(config)
    return UnslothTrainer(config)
