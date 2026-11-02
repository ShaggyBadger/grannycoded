"""Object storage backends that give uploaded images ULID-based filenames."""

from django.core.files.storage import FileSystemStorage, Storage, storages
from django.utils.deconstruct import deconstructible
from storages.backends.s3 import S3Storage

from home.asset_ids import ulid_filename


@deconstructible
class ULIDFileSystemStorage(FileSystemStorage):
    """Local-development storage with the same ULID naming convention as S3."""

    def get_available_name(self, name, max_length=None):
        return super().get_available_name(ulid_filename(name), max_length=max_length)


@deconstructible
class ULIDS3Storage(S3Storage):
    """S3-compatible storage that replaces incoming filenames with ULIDs."""

    def get_available_name(self, name, max_length=None):
        return super().get_available_name(ulid_filename(name), max_length=max_length)


@deconstructible
class PublicImageStorage(Storage):
    """Public image storage without serializing credentials into migrations."""

    @property
    def backend(self):
        return storages["public_images"]

    def _open(self, name, mode="rb"):
        return self.backend.open(name, mode)

    def _save(self, name, content):
        return self.backend._save(name, content)

    def get_available_name(self, name, max_length=None):
        return self.backend.get_available_name(
            ulid_filename(name), max_length=max_length
        )

    def get_valid_name(self, name):
        return self.backend.get_valid_name(name)

    def delete(self, name):
        return self.backend.delete(name)

    def exists(self, name):
        return self.backend.exists(name)

    def listdir(self, path):
        return self.backend.listdir(path)

    def size(self, name):
        return self.backend.size(name)

    def url(self, name):
        return self.backend.url(name)

    def path(self, name):
        return self.backend.path(name)


@deconstructible
class PrivateImageStorage(Storage):
    """Private image storage without serializing credentials into migrations."""

    @property
    def backend(self):
        return storages["private_images"]

    def _open(self, name, mode="rb"):
        return self.backend.open(name, mode)

    def _save(self, name, content):
        return self.backend._save(name, content)

    def get_available_name(self, name, max_length=None):
        return self.backend.get_available_name(
            ulid_filename(name), max_length=max_length
        )

    def get_valid_name(self, name):
        return self.backend.get_valid_name(name)

    def delete(self, name):
        return self.backend.delete(name)

    def exists(self, name):
        return self.backend.exists(name)

    def listdir(self, path):
        return self.backend.listdir(path)

    def size(self, name):
        return self.backend.size(name)

    def url(self, name):
        return self.backend.url(name)

    def path(self, name):
        return self.backend.path(name)
