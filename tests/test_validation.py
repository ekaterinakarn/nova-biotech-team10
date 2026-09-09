"""Ensure CSP evaluation isolates whole recording runs, not shuffled trials."""
import importlib.util
from pathlib import Path
import numpy as np

spec = importlib.util.spec_from_file_location('validation', Path(__file__).parents[1] / 'scripts/02_validate.py')
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


def test_csp_cross_validation_holds_out_entire_runs(monkeypatch):
    class Epochs:
        event_id = {'T1': 2, 'T2': 3}
        events = np.array([[0, 0, 2], [1, 0, 3]])
        def __getitem__(self, key): return self
        def __len__(self): return 2
        def get_data(self, copy=True): return np.ones((2, 12, 321))
    seen = []
    def load(subject, runs):
        assert len(runs) == 1
        seen.extend(runs)
        return Epochs()
    def evaluate(clf, X, y, cv, groups, error_score):
        assert X.shape == (6, 9, 321)
        splits = list(cv.split(X, y, groups))
        assert len(splits) == 3
        for train, test in splits:
            assert not set(groups[train]) & set(groups[test])
            assert len(set(groups[test])) == 1
        return np.array([.5, .5, .5])
    monkeypatch.setattr(validation.data, 'load_epochs', load)
    monkeypatch.setattr(validation, 'cross_val_score', evaluate)
    assert validation.csp_lda_accuracy(1, True) == (.5, 0)
    assert seen == [4, 8, 12]
