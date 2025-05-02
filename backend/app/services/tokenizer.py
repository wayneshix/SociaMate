"""
Tokenization service for estimating token counts in text.
"""
import tiktoken

# Default tokenizer model - matches the one used by our LLM
DEFAULT_TOKENIZER = "cl100k_base"  # For recent OpenAI models

class TokenizerService:
    def __init__(self, model_name=DEFAULT_TOKENIZER):
        """Initialize the tokenizer with the specified model."""
        self.tokenizer = tiktoken.get_encoding(model_name)
    
    def count_tokens(self, text):
        """Count the number of tokens in the provided text."""
        if not text:
            return 0
        tokens = self.tokenizer.encode(text)
        return len(tokens)
    
    def truncate_to_token_count(self, text, max_tokens):
        """Truncate text to fit within max_tokens."""
        if not text:
            return ""
        
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= max_tokens:
            return text
            
        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens)

# Create a global instance for convenience
tokenizer = TokenizerService() 