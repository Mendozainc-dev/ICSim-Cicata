from pathlib import Path
import sys
import tempfile
import unittest

MAIN_DIR = Path(__file__).resolve().parent.parent
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

from fuzzing.ids import RuleBasedIds, VulnerabilityReport


class DummyCanFrame:
    def __init__(self, arbitration_id: int, data: bytes):
        self.arbitration_id = arbitration_id
        self.data = data
        self.dlc = len(data)


class IdsAndVulnerabilityTests(unittest.TestCase):
    def test_vulnerability_classify_cwe400_flood(self):
        # Alta tasa de inyección (150 tramas/s) con anomalías -> CWE-400
        run_data = {
            "filename": "fuzz-flood.txt",
            "anomaly_count": 4,
            "rate": 150.0,
            "total_sent": 3000,
            "anomaly_notes": ["Tablero congelado ante ráfaga de paquetes"],
        }
        res = VulnerabilityReport.classify(run_data)
        cwe_ids = [c["cwe_id"] for c in res["classifications"]]
        self.assertIn("CWE-400", cwe_ids)

    def test_vulnerability_classify_cwe20_payload_range(self):
        # Tasa moderada pero con descalibración o anomalía de datos -> CWE-20
        run_data = {
            "filename": "fuzz-payload.txt",
            "anomaly_count": 2,
            "rate": 20.0,
            "total_sent": 500,
            "anomaly_notes": ["Aguja descalibrada con valores fuera de rango"],
        }
        res = VulnerabilityReport.classify(run_data)
        cwe_ids = [c["cwe_id"] for c in res["classifications"]]
        self.assertIn("CWE-20", cwe_ids)

    def test_vulnerability_classify_unclassified(self):
        # 0 anomalías -> Sin clasificar
        run_data = {
            "filename": "fuzz-clean.txt",
            "anomaly_count": 0,
            "rate": 10.0,
            "total_sent": 100,
            "anomaly_notes": [],
        }
        res = VulnerabilityReport.classify(run_data)
        cwe_ids = [c["cwe_id"] for c in res["classifications"]]
        self.assertIn("Sin clasificar", cwe_ids)

    def test_rule_based_ids_evaluates_all_three_rules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ids = RuleBasedIds(
                max_freq_hz=50.0,
                authorized_ids=[0x244, 0x188],
                max_speed_kmh=260.0,
                log_dir=Path(temp_dir),
            )

            frames = [
                # Regla 2: 0x244 con velocidad 300 km/h (bytes 3 y 4: 30000 = 0x7530)
                DummyCanFrame(0x244, b"\x00\x00\x00\x75\x30"),
                # Regla 3: ID 0x999 no autorizado (no está en whitelist [0x244, 0x188])
                DummyCanFrame(0x999, b"\x01\x02\x03\x04"),
            ]
            # Agregar 60 tramas de 0x188 en 0.5s para disparar Regla 1 (Frecuencia > 50 Hz)
            for _ in range(60):
                frames.append(DummyCanFrame(0x188, b"\x00\x00"))

            result = ids.evaluate_frames(frames=frames, duration=0.5)

            self.assertGreater(result["rule1_count"], 0)  # Frecuencia anómala
            self.assertGreater(result["rule2_count"], 0)  # Velocidad > 260 km/h
            self.assertGreater(result["rule3_count"], 0)  # ID 0x999 no autorizado
            self.assertGreaterEqual(result["alerts_count"], 3)

            # Probar guardado del reporte
            report_path = ids.save_evaluation_report(result)
            self.assertTrue(report_path.exists())
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("REPORTE DE EVALUACIÓN DE IDS AUTOMOTRIZ", content)
            self.assertIn("ISO/SAE 21434", content)


if __name__ == "__main__":
    unittest.main()
