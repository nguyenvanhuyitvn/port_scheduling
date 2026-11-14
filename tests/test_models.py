import unittest
from copy import deepcopy
from dataclasses import replace
from port_scheduler.domain import Instance, Vessel, Assignment, sequential, objective
from port_scheduler.validation import validate
from port_scheduler.mip import solve
from port_scheduler.heuristics import run


def example(L=200):
    return Instance(
        "test", L, 2, 35, [Vessel(x, 0, 100, 70, 1, 1) for x in ["A", "B"]], {}
    ).check()


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.ins = example()
        self.rows = [Assignment("A", 0, 2, 0, [1]), Assignment("B", 0, 2, 100, [2])]

    def test_parallel_valid(self):
        self.assertEqual(validate(self.ins, self.rows), [])

    def test_reuse_valid(self):
        self.assertEqual(validate(example(100), sequential(example(100))), [])

    def test_overlap(self):
        self.rows[1].position = 50
        self.assertTrue(any("berth-time" in e for e in validate(self.ins, self.rows)))

    def test_shared_crane(self):
        self.rows[1].cranes = [1]
        self.assertTrue(any("shared crane" in e for e in validate(self.ins, self.rows)))

    def test_crossing(self):
        self.rows[0].cranes = [2]
        self.rows[1].cranes = [1]
        self.assertTrue(any("crossing" in e for e in validate(self.ins, self.rows)))

    def test_missing(self):
        self.assertTrue(validate(self.ins, self.rows[:1]))

    def test_capacity(self):
        self.rows[0].end = 1
        self.assertTrue(any("capacity" in e for e in validate(self.ins, self.rows)))

    def test_boundary(self):
        self.rows[1].position = 150
        self.assertTrue(any("boundary" in e for e in validate(self.ins, self.rows)))

    def test_arrival(self):
        self.rows[0].start = -1
        self.assertTrue(any("arrival" in e for e in validate(self.ins, self.rows)))

    def test_noncontiguous(self):
        ins = Instance("test", 200, 3, 35, [Vessel("A", 0, 100, 70, 1, 3)], {}).check()
        self.assertTrue(
            any(
                "noncontiguous" in e
                for e in validate(ins, [Assignment("A", 0, 2, 0, [1, 3])])
            )
        )

    def test_invalid_input(self):
        self.ins.vessels[0] = replace(self.ins.vessels[0], length=201)
        with self.assertRaises(ValueError):
            self.ins.check()


class SolverTests(unittest.TestCase):
    def test_four_analytic_cases(self):
        for L, printed, expected in [
            (200, False, 4),
            (200, True, 6),
            (100, False, 6),
            (100, True, None),
        ]:
            with self.subTest(L=L, printed=printed):
                r = solve(example(L), "highs", 10, printed)
                if expected is None:
                    self.assertEqual(r["status"], "INFEASIBLE")
                else:
                    self.assertTrue(r["proven_optimal"], r)
                    self.assertAlmostEqual(r["objective"], expected, places=5)
                    self.assertFalse(validate(example(L), r["schedule"]))

    def test_single_variable_crane_duration(self):
        ins = Instance(
            "single", 100, 3, 35, [Vessel("A", 5, 100, 210, 1, 3)], {}
        ).check()
        r = solve(ins, "highs", 10)
        self.assertTrue(r["proven_optimal"])
        self.assertAlmostEqual(r["objective"], 2, places=5)

    def test_three_vessel_resource_case(self):
        ins = Instance(
            "three",
            200,
            2,
            35,
            [Vessel(x, 0, 100, 70, 1, 1) for x in ["A", "B", "C"]],
            {},
        ).check()
        r = solve(ins, "highs", 10)
        self.assertTrue(r["proven_optimal"])
        self.assertAlmostEqual(r["objective"], 8, places=5)

    def test_reproducible_generation_runs(self):
        for alg in ["ga", "gga"]:
            a = run(example(), alg, seconds=None, generations=5, population=8, seed=42)
            b = run(example(), alg, seconds=None, generations=5, population=8, seed=42)
            self.assertEqual(a["objective"], b["objective"])
            self.assertEqual(a["schedule"], b["schedule"])
            self.assertFalse(validate(example(), a["schedule"]))
            self.assertLessEqual(a["objective"], 6)


if __name__ == "__main__":
    unittest.main()
