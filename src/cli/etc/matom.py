# file: src/cli/etc/matom.py
import sys

M_NU = 1e-37  # neutrino mass in kg

def encode_normalized(value_kg, m_nu=M_NU):
    if value_kg <= 0:
        return 0, 0
    best = None
    for E in range(256):
        denom = (2.0 ** E) * m_nu
        s = value_kg / denom
        M = int(round(256 * (s - 1)))
        M = max(0, min(255, M))
        represented = (1 + M / 256) * denom
        rel_error = abs(represented - value_kg) / value_kg
        if best is None or rel_error < best[2]:
            best = (E, M, rel_error)
    return best[0], best[1]

def main():
    if len(sys.argv) < 2:
        print("Usage: biou nnn <mass_in_kg>")
        sys.exit(1)
    try:
        mass = float(sys.argv[1])
    except ValueError:
        print(f"Invalid number: {sys.argv[1]}")
        sys.exit(1)

    E, M = encode_normalized(mass)
    print(f"Mass: {mass} kg")
    print(f"Encoded (Exponent, Mantissa): ({E}, {M})")
    print(f"Bytes (hex): {E:02X} {M:02X}")
    represented = (1 + M / 256) * (2 ** E) * M_NU
    print(f"Represented mass: {represented:.6E} kg")
    rel_error = abs(represented - mass) / mass * 100 if mass != 0 else 0
    print(f"Relative error: {rel_error:.6f}%")

if __name__ == "__main__":
    main()
