from dataclasses import dataclass
from datasets import Dataset


@dataclass
class Textbook():
  """Class storing textbook metadata"""
  idiom: str
  subject: str
  grade_volume: str
  book_type: str
  ISBN: str | None = None
  hf_dataset: Dataset = Dataset.from_dict({})
  textbook_path: str = ""