from pathlib import Path
import sys
import tempfile
import unittest

MAIN_DIR = Path(__file__).resolve().parent.parent
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

from fuzzing.analysis import RunAnalyzer


SAMPLE_REPORT_TEXT = """REPORTE DE EJECUCIÓN - FUZZER CAN
======================================
Inicio: 2026-10-15T01:00:00+00:00
Fin: 2026-10-15T01:00:10+00:00
Interfaz: vcan0
Modo: random
IDs objetivo: 0x080, 0x110, 0x188, 0x244, 0x133
Delay configurado: 0.01 s
Límite de tramas: 1000
Límite de duración: sin límite s
Semilla: 12345
Tramas en corpus: no aplica
CSV de salida: no solicitado

RESULTADO
Estado: Límite de tramas alcanzado (1000)
Tramas enviadas: 1000
Duración real: 10.000 s
Tasa media: 100.00 tramas/s
Tramas por ID:
  0x080: 200
  0x110: 200
  0x188: 200
  0x244: 200
  0x133: 200

CONCLUSIÓN
Se enviaron 1000 tramas y la ejecución terminó por: Límite de tramas alcanzado (1000).
"""


class RunAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temp_dir.name)
        self.report_file = self.log_dir / "fuzz-test-20261015-010000.txt"
        self.report_file.write_text(SAMPLE_REPORT_TEXT, encoding="utf-8")
        self.analyzer = RunAnalyzer(log_dir=self.log_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_report_file(self):
        data = self.analyzer.parse_report_file(self.report_file)
        self.assertEqual(data["total_sent"], 1000)
        self.assertEqual(data["duration"], 10.0)
        self.assertEqual(data["rate"], 100.0)
        self.assertEqual(data["mode"], "random")
        self.assertIn(0x244, data["sent_by_id"])
        self.assertFalse(data["has_metrics"])

    def test_compute_metrics_with_anomalies(self):
        # 5 anomalías en 1000 tramas = 0.50% de tasa
        metrics = self.analyzer.compute_metrics(total_sent=1000, anomaly_count=5, recovery_latency=2.5)
        self.assertEqual(metrics["total_sent"], 1000)
        self.assertEqual(metrics["anomaly_count"], 5)
        self.assertEqual(metrics["anomaly_rate"], 0.50)
        self.assertEqual(metrics["recovery_latency"], 2.50)

    def test_compute_metrics_zero_anomalies(self):
        metrics = self.analyzer.compute_metrics(total_sent=500, anomaly_count=0, recovery_latency=0.0)
        self.assertEqual(metrics["anomaly_rate"], 0.0)
        self.assertEqual(metrics["anomaly_count"], 0)

    def test_append_metrics_to_report(self):
        success = self.analyzer.append_metrics_to_report(
            report_path=self.report_file,
            anomaly_count=3,
            recovery_latency=1.8,
            notes=["Aguja de velocímetro oscilando", "Luces de giro bloqueadas"],
        )
        self.assertTrue(success)

        updated = self.analyzer.parse_report_file(self.report_file)
        self.assertTrue(updated["has_metrics"])
        self.assertEqual(updated["anomaly_count"], 3)
        self.assertEqual(updated["anomaly_rate"], 0.30)
        self.assertEqual(updated["recovery_latency"], 1.80)

        # Verificar que el contenido previo sigue intacto
        content = self.report_file.read_text(encoding="utf-8")
        self.assertIn("REPORTE DE EJECUCIÓN - FUZZER CAN", content)
        self.assertIn("Tramas enviadas: 1000", content)
        self.assertIn("ANÁLISIS DE IMPACTO Y MÉTRICAS (FASE 4)", content)
        self.assertIn("Tasa de anomalías detectadas: 0.30%", content)


if __name__ == "__main__":
    unittest.main()
