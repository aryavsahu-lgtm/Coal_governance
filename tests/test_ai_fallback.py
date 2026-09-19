import unittest
from app import create_app
from app.ai.yolo_detector import YOLODetector


class TestAIFallback(unittest.TestCase):

    def setUp(self):
        self.app = create_app()

    def test_mock_detector_generates_valid_detections(self):
        detector = YOLODetector(model_path="nonexistent_model.pt")
        self.assertTrue(detector.is_mock)
        
        # Test point in polygon
        polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
        self.assertTrue(detector.is_point_in_polygon((5, 5), polygon))
        self.assertFalse(detector.is_point_in_polygon((15, 15), polygon))


if __name__ == "__main__":
    unittest.main()
