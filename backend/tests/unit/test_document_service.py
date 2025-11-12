import unittest
from unittest.mock import MagicMock
import uuid
from io import BytesIO

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.document_service.application.services.document_service_impl import (
    DocumentServiceImpl,
)
from services.document_service.application.domain.document_job import (
    DocumentJob,
    DocumentType,
)
from services.document_service.application.exceptions import (
    JobNotFoundError,
    JobAccessForbiddenError,
)
from services.document_service.application.ports.output.document_job_repository import (
    DocumentJobRepository,
)
from services.document_service.application.ports.output.file_storage import FileStorage
from services.document_service.application.ports.output.message_queue import (
    MessageQueue,
)


class TestDocumentService(unittest.TestCase):
    def setUp(self):
        self.mock_job_repo = MagicMock(spec=DocumentJobRepository)
        self.mock_file_storage = MagicMock(spec=FileStorage)
        self.mock_message_queue = MagicMock(spec=MessageQueue)

        self.doc_service = DocumentServiceImpl(
            job_repository=self.mock_job_repo,
            file_storage=self.mock_file_storage,
            message_queue=self.mock_message_queue,
            ocr_queue_name="test_ocr_queue",
        )

        self.user_id = uuid.uuid4()
        self.job_id = uuid.uuid4()
        self.test_job = DocumentJob(
            id=self.job_id,
            user_id=self.user_id,
            file_path=f"documents/{self.user_id}/test.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        )

    def test_start_document_processing_success(self):
        # Arrange
        file_content = BytesIO(b"dummy file content")
        file_name = "test.pdf"

        self.mock_file_storage.upload.return_value = (
            f"documents/{self.user_id}/some-uuid.pdf"
        )
        self.mock_job_repo.save.return_value = self.test_job

        # Act
        result = self.doc_service.start_document_processing(
            user_id=self.user_id,
            file_name=file_name,
            file_content=file_content,
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        )

        # Assert
        self.mock_file_storage.upload.assert_called_once()
        self.mock_job_repo.save.assert_called_once()
        self.mock_message_queue.publish_message.assert_called_once_with(
            queue_name="test_ocr_queue",
            message={
                "job_id": str(self.job_id),
                "file_path": self.test_job.file_path,
                "document_type": self.test_job.document_type.value,
            },
        )
        self.assertEqual(result.id, self.job_id)

    def test_get_job_status_success(self):
        # Arrange
        self.mock_job_repo.get_by_id.return_value = self.test_job

        # Act
        result = self.doc_service.get_job_status(
            job_id=self.job_id, user_id=self.user_id
        )

        # Assert
        self.mock_job_repo.get_by_id.assert_called_once_with(self.job_id)
        self.assertEqual(result.id, self.job_id)

    def test_get_job_status_not_found(self):
        # Arrange
        self.mock_job_repo.get_by_id.return_value = None

        # Act & Assert
        with self.assertRaises(JobNotFoundError):
            self.doc_service.get_job_status(job_id=self.job_id, user_id=self.user_id)

    def test_get_job_status_forbidden(self):
        # Arrange
        other_user_id = uuid.uuid4()
        self.mock_job_repo.get_by_id.return_value = self.test_job

        # Act & Assert
        with self.assertRaises(JobAccessForbiddenError):
            self.doc_service.get_job_status(job_id=self.job_id, user_id=other_user_id)

    def test_get_user_jobs(self):
        # Arrange
        self.mock_job_repo.get_by_user_id.return_value = [self.test_job, self.test_job]

        # Act
        result = self.doc_service.get_user_jobs(user_id=self.user_id)

        # Assert
        self.mock_job_repo.get_by_user_id.assert_called_once_with(self.user_id)
        self.assertEqual(len(result), 2)

    def test_start_document_processing_invalid_extension(self):
        file_content = BytesIO(b"dummy file content")
        file_name = "test.txt"

        with self.assertRaises(ValueError):
            self.doc_service.start_document_processing(
                user_id=self.user_id,
                file_name=file_name,
                file_content=file_content,
                document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            )


if __name__ == "__main__":
    unittest.main()
