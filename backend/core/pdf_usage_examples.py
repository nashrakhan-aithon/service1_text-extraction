"""Examples of how to use the unified PDF service across all backend services."""

from backend.core import PDFService, quick_extract_text, quick_convert_to_image


# Example 1: Using PDFService class (recommended for complex operations)
def process_document_with_service(pdf_path: str):
    """Example: Using PDFService class for complex operations."""
    with PDFService() as pdf_service:
        # Open PDF
        page_count = pdf_service.open_pdf(pdf_path)
        print(f"PDF has {page_count} pages")

        # Get PDF info
        info = pdf_service.get_pdf_info()
        print(f"PDF metadata: {info['metadata']}")

        # Extract text from first page
        text = pdf_service.extract_text(0)
        print(f"Page 1 text: {text[:100]}...")

        # Convert first page to image
        image_base64 = pdf_service.convert_to_image(0, zoom=2.0)
        print(f"Page 1 image: {len(image_base64)} characters")

        # Extract full text
        full_text = pdf_service.extract_full_text()
        print(f"Full text length: {len(full_text)} characters")

        # PDF is automatically closed when exiting context manager


# Example 2: Using quick functions (recommended for simple operations)
def quick_operations_example(pdf_path: str):
    """Example: Using quick functions for simple operations."""
    # Quick text extraction
    text = quick_extract_text(pdf_path, page_num=0)
    print(f"Page 1 text: {text[:100]}...")

    # Quick image conversion
    image_base64 = quick_convert_to_image(pdf_path, page_num=0, zoom=2.0)
    print(f"Page 1 image: {len(image_base64)} characters")

    # Quick page count
    page_count = quick_get_page_count(pdf_path)
    print(f"PDF has {page_count} pages")


# Example 3: Service-specific usage patterns
class DocumentProcessingService:
    """Example: How document_processing service should use PDF service."""

    def __init__(self):
        self.pdf_service = PDFService()

    async def process_document(self, pdf_path: str):
        """Process document for document_processing service."""
        with PDFService() as pdf_service:
            pdf_service.open_pdf(pdf_path)

            # Document processing specific logic
            page_count = pdf_service.get_pdf_info()["page_count"]

            for page_num in range(page_count):
                # Extract text
                text = pdf_service.extract_text(page_num)

                # Convert to image for AI processing
                image_base64 = pdf_service.convert_to_image(page_num)

                # Process page (document-specific logic)
                await self._process_page(page_num, text, image_base64)

    async def _process_page(self, page_num: int, text: str, image_base64: str):
        """Process individual page (document-specific logic)."""
        # Document processing specific implementation
        pass


class BrokerageExtractionService:
    """Example: How brokerage_extraction service should use PDF service."""

    async def extract_brokerage_fields(self, pdf_path: str):
        """Extract brokerage-specific fields."""
        with PDFService() as pdf_service:
            pdf_service.open_pdf(pdf_path)

            # Brokerage extraction specific logic
            page_count = pdf_service.get_pdf_info()["page_count"]

            for page_num in range(page_count):
                # Extract text for field extraction
                text = pdf_service.extract_text(page_num)

                # Convert to image for AI field extraction
                image_base64 = pdf_service.convert_to_image(page_num)

                # Extract brokerage fields (brokerage-specific logic)
                fields = await self._extract_brokerage_fields_from_page(
                    page_num, text, image_base64
                )

                # Save extracted fields
                await self._save_brokerage_fields(page_num, fields)

    async def _extract_brokerage_fields_from_page(
        self, page_num: int, text: str, image_base64: str
    ):
        """Extract brokerage fields from page (brokerage-specific logic)."""
        # Brokerage extraction specific implementation
        pass

    async def _save_brokerage_fields(self, page_num: int, fields: dict):
        """Save extracted brokerage fields (brokerage-specific logic)."""
        # Brokerage saving specific implementation
        pass


# Example 4: Error handling
def robust_pdf_processing(pdf_path: str):
    """Example: Robust PDF processing with error handling."""
    try:
        with PDFService() as pdf_service:
            pdf_service.open_pdf(pdf_path)

            # Process with error handling
            page_count = pdf_service.get_pdf_info()["page_count"]

            for page_num in range(page_count):
                try:
                    text = pdf_service.extract_text(page_num)
                    image_base64 = pdf_service.convert_to_image(page_num)

                    # Process page
                    print(f"Processed page {page_num + 1}")

                except Exception as e:
                    print(f"Error processing page {page_num + 1}: {str(e)}")
                    continue

    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {str(e)}")
        raise


# Example 5: Batch processing
async def batch_process_documents(pdf_paths: list):
    """Example: Batch processing multiple PDFs."""
    results = []

    for pdf_path in pdf_paths:
        try:
            with PDFService() as pdf_service:
                pdf_service.open_pdf(pdf_path)

                # Process document
                page_count = pdf_service.get_pdf_info()["page_count"]
                full_text = pdf_service.extract_full_text()

                results.append(
                    {
                        "pdf_path": pdf_path,
                        "page_count": page_count,
                        "text_length": len(full_text),
                        "status": "success",
                    }
                )

        except Exception as e:
            results.append({"pdf_path": pdf_path, "error": str(e), "status": "error"})

    return results
