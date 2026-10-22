import unittest
from unittest.mock import Mock, patch
import pandas as pd
from src.istat_population import API_URL, download_population, regional_changes


class RegionalChangesTests(unittest.TestCase):
    def test_computes_percent_and_excludes_provinces(self):
        df = pd.DataFrame({
            "ITTER107": ["ITC1", "ITC1", "ITC11", "ITC11", "ITF3", "ITF3"],
            "TIME_PERIOD": ["2014", "2024", "2014", "2024", "2014", "2024"],
            "OBS_VALUE": [100, 110, 20, 25, 200, 180],
        })
        result = regional_changes(df, 2014, 2024)
        self.assertEqual(set(result["codice_regione"]), {"ITC1", "ITF3"})
        north = result.set_index("codice_regione").loc["ITC1"]
        self.assertAlmostEqual(north["variazione_percentuale"], 10.0)
        south = result.set_index("codice_regione").loc["ITF3"]
        self.assertAlmostEqual(south["variazione_percentuale"], -10.0)

    @patch("src.istat_population.requests.get")
    def test_download_uses_https_endpoint_and_end_period_workaround(self, mock_get):
        response = Mock()
        response.text = "REF_AREA,TIME_PERIOD,OBS_VALUE\nITC1,2014,100\nITC1,2024,110\n"
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        df = download_population(2014, 2024)

        self.assertEqual(len(df), 2)
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], API_URL)
        self.assertTrue(args[0].startswith("https://"))
        self.assertEqual(kwargs["params"], {"startPeriod": 2014, "endPeriod": 2023})

    def test_rejects_duplicate_observations(self):
        df = pd.DataFrame({
            "REF_AREA": ["ITC1", "ITC1", "ITC1"],
            "TIME_PERIOD": ["2014", "2024", "2024"],
            "OBS_VALUE": [100, 110, 111],
        })
        with self.assertRaisesRegex(RuntimeError, "Multiple observations"):
            regional_changes(df, 2014, 2024)


if __name__ == "__main__":
    unittest.main()
