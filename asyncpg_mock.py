"""Mock asyncpg module for testing when real asyncpg is not available."""

class MockPool:
    async def execute(self, *args, **kwargs):
        return None
    
    async def fetch(self, *args, **kwargs):
        return []
    
    async def fetchrow(self, *args, **kwargs):
        return None
    
    async def close(self):
        pass

async def create_pool(*args, **kwargs):
    return MockPool()

class Record(dict):
    pass

ConnectionDoesNotExistError = Exception
