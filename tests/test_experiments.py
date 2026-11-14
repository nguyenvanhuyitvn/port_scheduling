import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import tempfile
import unittest
from dataclasses import asdict
import pandas as pd
from port_scheduler.experiments import Config, run_matrix, from_frame, aggregate
from port_scheduler.domain import Instance, Vessel, write_json


class ExperimentTests(unittest.TestCase):
    def test_reject_fractional_crane_quantity(self):
        f = pd.DataFrame(
            [dict(id="A", eta=0, length=100, workload=70, q_min=1.5, q_max=2)]
        )
        with self.assertRaises(ValueError):
            from_frame(f, "bad", 200, 2, 35)

    def test_resume_preserves_run_and_configuration_separates(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            p = td / "input.json"
            write_json(
                p,
                asdict(
                    Instance("tiny", 200, 2, 35, [Vessel("A", 0, 100, 70, 1, 1)], {})
                ),
            )
            c = Config(mode="generations", generations=1, population=4)
            root, r, s, e = run_matrix([p], ["gga"], [0], c, td / "out")
            rp = Path(r.iloc[0].run_path)
            timestamp = rp.stat().st_mtime_ns
            run_matrix([p], ["gga"], [0], c, td / "out")
            self.assertEqual(timestamp, rp.stat().st_mtime_ns)
            other, _, _, _ = run_matrix(
                [p], ["gga"], [0], Config(seconds=0.05), td / "out"
            )
            self.assertNotEqual(root, other)
            self.assertTrue(bool(r.iloc[0].feasible))
            self.assertAlmostEqual(s.iloc[0]["best"], 2.0)

    def test_no_infeasible_value_in_mean_and_no_config_mixing(self):
        r = pd.DataFrame(
            [
                dict(
                    experiment_id="a",
                    data_sha256="x",
                    instance="I",
                    n=5,
                    algorithm="ga",
                    feasible=True,
                    objective=10,
                    wall_seconds=1,
                    proven_optimal=False,
                ),
                dict(
                    experiment_id="a",
                    data_sha256="x",
                    instance="I",
                    n=5,
                    algorithm="ga",
                    feasible=False,
                    objective=None,
                    wall_seconds=1,
                    proven_optimal=False,
                ),
                dict(
                    experiment_id="b",
                    data_sha256="x",
                    instance="I",
                    n=5,
                    algorithm="ga",
                    feasible=True,
                    objective=100,
                    wall_seconds=1,
                    proven_optimal=False,
                ),
            ]
        )
        s = aggregate(r)
        self.assertEqual(len(s), 2)
        a = s[s.experiment_id == "a"].iloc[0]
        self.assertEqual(a["mean"], 10)
        self.assertEqual(a.feasible_rate, 0.5)

    def test_ablation_variants_feasible_and_seed_with_greedy(self):
        from port_scheduler.domain import load_instance
        from port_scheduler.heuristics import run

        ins = load_instance(
            Path(__file__).resolve().parents[1] / "data" / "liaoning_12.json"
        )
        greedy = run(ins, "greedy", None, 1)["objective"]
        for alg in ["ga", "gga", "ga_greedy", "ga_repair"]:
            r = run(ins, alg, None, 2, population=8, seed=0)
            self.assertTrue(r["feasible"], alg)
            self.assertEqual(r["validation_errors"], [])
            if alg in {"gga", "ga_greedy"}:
                self.assertLessEqual(r["objective"], greedy + 1e-6)


if __name__ == "__main__":
    unittest.main()
