import unittest
import numpy as np
from src.experiment import (
    cable, after_experience, transfers, native_basis, index_cosine_basis,
    delta_log_amplitude, N, TIPS, WRITE_BUDGET
)

class CableTest(unittest.TestCase):
    def test_conductance_symmetric_positive_definite(self):
        m = cable(11)
        np.testing.assert_allclose(m.G, m.G.T, atol=1e-14)
        self.assertGreater(np.min(np.linalg.eigvalsh(m.G)), 0)

    def test_pulse_causes_matched_local_write(self):
        m = cable(2)
        for arm in range(4):
            after, delta = after_experience(m, arm)
            self.assertAlmostEqual(float(delta.sum()), WRITE_BUDGET)
            self.assertEqual(int(np.argmax(delta)), int(TIPS[arm]))
            np.testing.assert_allclose(after.G - m.G, np.diag(delta), atol=1e-14)

    def test_repeatability_and_state_only_control(self):
        m = cable(9)
        pre = transfers(m)
        np.testing.assert_allclose(transfers(m), pre, rtol=0, atol=0)
        changed, _ = after_experience(m, 1)
        self.assertGreater(np.linalg.norm(delta_log_amplitude(pre, transfers(changed))), .01)

    def test_graph_and_cosine_are_c_orthonormal(self):
        m = cable(2)
        for V in (native_basis(m), index_cosine_basis(m)):
            np.testing.assert_allclose(V.T @ (m.C[:, None] * V), np.eye(8), atol=1e-11)

if __name__ == '__main__':
    unittest.main()
