from pydantic import BaseModel

from virtualship.cli._fetch import (
    create_hash,
    filename_to_hash,
    hash_model,
    hash_to_filename,
)


def test_create_hash():
    assert len(create_hash("correct-length")) == 8
    assert create_hash("same") == create_hash("same")
    assert create_hash("unique1") != create_hash("unique2")


def test_hash_filename_roundtrip():
    hash_ = create_hash("test")
    assert filename_to_hash(hash_to_filename(hash_)) == hash_


def test_hash_model():
    class TestModel(BaseModel):
        a: int
        b: str

    hash_model(TestModel(a=0, b="b"))
