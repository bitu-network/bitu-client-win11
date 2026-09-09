# file: src/cli/etc/factor/factor.py
import sys
from collections import Counter

def prime_factors(n: int) -> Counter:
    """Return a Counter of prime factors of n."""
    i = 2
    factors = Counter()
    while i * i <= n:
        while n % i == 0:
            factors[i] += 1
            n //= i
        i += 1
    if n > 1:
        factors[n] += 1
    return factors

def fingerprint_str(n: int) -> str:
    """Return a string representation of the factor fingerprint."""
    factors = prime_factors(n)
    return " * ".join(f"{p}^{exp}" if exp > 1 else f"{p}" for p, exp in sorted(factors.items()))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python factor_fingerprint.py <number>")
        sys.exit(1)
    try:
        num = int(sys.argv[1])
        if num <= 0:
            raise ValueError
    except ValueError:
        print("[x] Please provide a positive integer.")
        sys.exit(1)

    print(f"{num} => {fingerprint_str(num)}")
