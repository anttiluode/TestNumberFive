"""Reproducible Python reference for the browser computation."""
from pathlib import Path
import json
from .experiment import cable, after_experience, transfers


def pair_complex(arr):
    return [[[float(z.real), float(z.imag)] for z in row] for row in arr]


def main():
    model = cable(42)
    pre = pair_complex(transfers(model))
    post = [pair_complex(transfers(after_experience(model, b)[0])) for b in range(4)]
    content = {
        'G': model.G.tolist(), 'C': model.C.tolist(), 'leak': model.leak.tolist(),
        'edges': [list(x) for x in model.edges],
        'reference': {'before': pre, 'after': post},
    }
    target = Path('web/demo.json')
    target.write_text(json.dumps(content, separators=(',', ':')) + '\n')
    print('Wrote', target)

if __name__ == '__main__':
    main()
