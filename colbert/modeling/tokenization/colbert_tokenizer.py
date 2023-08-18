import torch
from colbert.utils.utils import insert_constant_column


def insert_constant_column(arr, pos, fill_value):
    """Insert a column of `fill_value` at the specified position in a 2D array"""
    begin, end = arr[:, :pos], arr[:, pos:]
    fill = torch.full_like(arr[:, 0], fill_value).unsqueeze(-1)
    return torch.cat([begin, fill, end], dim=-1)


class ColbertTokenizer:
    def __init__(
        self,
        raw_tokenizer,
        max_length: int,
        marker_token: str,
        marker_token_position: int,
        attend_to_mask_tokens: bool = False,
        mask_expand_token: str = None,
        tokenizer_alias: str = 'TokenizerAliasPlaceholder',
        tokenizer_kwargs: dict = None,
    ):
        """Base class for ColBERT tokenizers.

        Args:
            raw_tokenizer (PretrainedTokenizerFast): The raw tokenizer.
            max_length (int): The maximum length of the tokenized text.
            marker_token (str): The marker token.
            marker_token_position (int): The position of the marker token.
                For BERT models this is 1, for T5 models this is 0.
            attend_to_mask_tokens (bool, optional): Whether to attend to mask
                tokens. Defaults to False.
            mask_expand_token (str, optional): The mask expand token. Defaults
                to None. Usually only queries are expanded with mask tokens.
            tokenizer_alias (str, optional): The name of the tokenizer. Defaults
                to 'TokenizerAliasPlaceholder'.
            tokenizer_kwargs (dict, optional): Keyword arguments for the
                tokenizer. Defaults to {}.
        """
        self.tok = raw_tokenizer
        self.max_length = max_length
        self.marker_token = marker_token
        self.marker_token_position = marker_token_position
        # self.background_maxlen = 512 - self.query_maxlen + 1  # FIXME: Make this configurable
        self.attend_to_mask_tokens = attend_to_mask_tokens
        self.mask_expand_token = mask_expand_token
        self.mask_expand_token_id = self.tok.convert_tokens_to_ids(
            self.mask_expand_token)
        self.tokenizer_alias = tokenizer_alias
        self.tokenizer_kwargs = tokenizer_kwargs or {}

        self.marker_token_id = self.tok.convert_tokens_to_ids(
            self.marker_token)
        # self.marker_token_id cannot be None or equal to unk_token_id or pad_token_id
        if (self.marker_token_id is None
                or self.marker_token_id == self.tokenizer.unk_token_id
                or self.marker_token_id == self.tokenizer.pad_token_id):
            raise ValueError(
                f"marker_token_id cannot be None or equal to unk_token_id or pad_token_id. "
            )
        self.is_used = False

    def encode_texts(self, texts):
        """Encode a list of texts and return the input ids and attention mask."""
        obj = self.tok(texts, **self.tokenizer_kwargs)
        ids, mask = obj['input_ids'], obj['attention_mask']
        return ids, mask

    def add_marker_token(self, ids, mask):
        ids = insert_constant_column(ids, self.marker_token_position,
                                     self.marker_token_id)
        mask = insert_constant_column(mask, self.marker_token_position, 1)
        return ids, mask

    def process_mask_expansion(self, ids, mask):
        if self.mask_expand_token is not None:
            ids[ids == self.pad_token_id] = self.mask_expand_token_id
        if self.attend_to_mask_tokens and self.mask_expand_token is not None:
            mask[ids == self.mask_token_id] = 1
            assert mask.sum().item() == mask.size(0) * mask.size(1), mask
        return ids, mask

    def debug_once(self, batch_text, bsize, ids, mask):
        if self.is_used is False:
            self.is_used = True
            print()
            print(
                f"#>{self.__class__.__name__}.tensorize(batch_text, bsize) ==")
            print(f"#>{self.tokenizer_alias}.tensorize(batch_text, bsize) ==")
            print(f"#> Input: {batch_text[0]}, \t\t {bsize}")
            print(f"#> Output IDs: {ids[0].size()}, {ids[0]}")
            print(f"#> Output Mask: {mask[0].size()}, {mask[0]}")
            print()
