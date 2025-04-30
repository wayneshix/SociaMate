from .message import Message, Base as MessageBase
from .chunk import MessageChunk, Base as ChunkBase
from .summary import Summary, Base as SummaryBase
 
# Export bases for database initialization
models_bases = [MessageBase, ChunkBase, SummaryBase] 