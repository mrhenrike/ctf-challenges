#!/usr/bin/env python3 -I
"""
Solve ECDLP for "A Map of Small Things" (POCTF 2026, ID=73).
Curve: y^2 = x^3 + x over Fp (a=1, b=0)
p = 17759930830448937043 (~64 bits)

Strategy: compute curve order, factor it, use Pohlig-Hellman with BSGS per subgroup.
"""
import math
import sys

# Curve parameters
p = 17759930830448937043
a = 1
b = 0

# Generator
Gx = 2
Gy = 2130375071143573863

# Target public key
Qx = 310951215520125117
Qy = 6072823342940074756


def modinv(a, m):
    """Extended Euclidean algorithm for modular inverse."""
    if a < 0:
        a = a % m
    g, x, _ = extended_gcd(a, m)
    if g != 1:
        return None  # No inverse
    return x % m


def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x, y = extended_gcd(b % a, a)
    return g, y - (b // a) * x, x


def point_add(P, Q):
    """Add two points on the curve."""
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q
    if x1 == x2:
        if (y1 + y2) % p == 0:
            return None  # Point at infinity
        # Point doubling
        num = (3 * x1 * x1 + a) % p
        den = modinv(2 * y1, p)
        if den is None:
            return None
        lam = (num * den) % p
    else:
        num = (y2 - y1) % p
        den = modinv((x2 - x1) % p, p)
        if den is None:
            return None
        lam = (num * den) % p

    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p
    return (x3, y3)


def point_mul(k, P):
    """Scalar multiplication using double-and-add."""
    if k == 0 or P is None:
        return None
    if k < 0:
        P = (P[0], (-P[1]) % p)
        k = -k
    result = None
    addend = P
    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1
    return result


def curve_order_naive():
    """
    For small p, we can use Schoof's algorithm concept,
    but for ~64-bit p, let's try computing #E(Fp) using
    the Legendre symbol method (counting points).

    Actually for p ~ 1.78e19, counting all points is infeasible.
    Let's try a different approach: use the fact that for
    y^2 = x^3 + x over Fp, the order has specific properties.

    For the curve y^2 = x^3 + x (a=1, b=0):
    - If p = 3 mod 4, then #E = p + 1
    - If p = 1 mod 4, more analysis needed
    """
    # Check p mod 4
    print(f"p mod 4 = {p % 4}")
    print(f"p mod 3 = {p % 3}")

    # For y^2 = x^3 + x, this is a special curve.
    # Let's check: p mod 4
    if p % 4 == 3:
        # For y^2 = x^3 + x with p = 3 mod 4, #E(Fp) = p + 1
        return p + 1

    # Otherwise, need to compute. Let's try baby-step giant-step on a small
    # multiple first to find the order of G.
    return None


def bsgs(G, Q, n):
    """Baby-step Giant-step to find k such that Q = k*G in group of order n."""
    m = math.isqrt(n) + 1

    # Baby step: compute j*G for j = 0..m-1
    baby = {}
    current = None  # 0*G = infinity
    for j in range(m):
        if current is None:
            baby[None] = j
        else:
            baby[current[0]] = (j, current)
        current = point_add(current, G)

    # Giant step: compute Q - i*m*G for i = 0..m-1
    # We need -m*G
    mG = point_mul(m, G)
    neg_mG = (mG[0], (-mG[1]) % p) if mG else None

    gamma = Q
    for i in range(m):
        if gamma is None:
            if None in baby:
                j = baby[None]
                return (i * m + j) % n
        else:
            if gamma[0] in baby:
                j_data = baby[gamma[0]]
                if isinstance(j_data, tuple):
                    j, pt = j_data
                    # Verify y coordinate matches
                    if pt[1] == gamma[1]:
                        return (i * m + j) % n
                    else:
                        # It's the negation: j*G has -y
                        # So gamma = -(j*G), meaning k*G = -(j*G) + i*m*G
                        # This doesn't directly give us k, skip
                        pass
                else:
                    j = j_data
                    return (i * m + j) % n
        gamma = point_add(gamma, neg_mG)

    return None


def factor_trial(n, limit=10**7):
    """Trial division factoring."""
    factors = {}
    d = 2
    while d * d <= n and d < limit:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


def pohlig_hellman(G, Q, n, factors):
    """Pohlig-Hellman algorithm for discrete log."""
    residues = []
    moduli = []

    for prime, exp in factors.items():
        pe = prime ** exp
        # Compute generators for subgroup of order pe
        cofactor = n // pe
        Gi = point_mul(cofactor, G)
        Qi = point_mul(cofactor, Q)

        if Gi is None:
            print(f"  [!] Subgroup generator is identity for prime {prime}^{exp}")
            continue

        print(f"  Solving for prime {prime}^{exp} (subgroup)...")

        if exp == 1:
            # Simple BSGS
            ki = bsgs(Gi, Qi, prime)
            if ki is not None:
                print(f"    k mod {prime} = {ki}")
                residues.append(ki)
                moduli.append(prime)
            else:
                print(f"    [!] BSGS failed for prime {prime}")
        else:
            # For prime powers, use iterative method
            ki = 0
            gamma = Qi
            Gi_base = point_mul(pe // prime, Gi)  # Generator of order prime

            for j in range(exp):
                power = pe // (prime ** (j + 1))
                h = point_mul(power, gamma)
                dj = bsgs(Gi_base, h, prime)
                if dj is None:
                    print(f"    [!] BSGS failed at iteration {j}")
                    break
                ki += dj * (prime ** j)
                # Update gamma
                inv_point = point_mul(dj * (prime ** j), G)
                inv_point = point_mul(cofactor, inv_point)
                inv_point = (inv_point[0], (-inv_point[1]) % p) if inv_point else None
                gamma = point_add(gamma, inv_point)

            print(f"    k mod {pe} = {ki}")
            residues.append(ki)
            moduli.append(pe)

    # CRT
    return crt(residues, moduli)


def crt(residues, moduli):
    """Chinese Remainder Theorem."""
    if not residues:
        return None
    M = 1
    for m in moduli:
        M *= m

    x = 0
    for ri, mi in zip(residues, moduli):
        Mi = M // mi
        yi = modinv(Mi, mi)
        if yi is None:
            return None
        x = (x + ri * Mi * yi) % M

    return x


def main():
    G = (Gx, Gy)
    Q = (Qx, Qy)

    # Verify points are on the curve
    for name, pt in [("G", G), ("Q", Q)]:
        lhs = (pt[1] * pt[1]) % p
        rhs = (pt[0]**3 + a * pt[0] + b) % p
        assert lhs == rhs, f"{name} is not on the curve!"
    print("[+] Both points verified on curve")

    # Compute curve order
    # For y^2 = x^3 + x:
    print(f"[*] p = {p}")
    print(f"[*] p mod 4 = {p % 4}")

    order = None
    if p % 4 == 3:
        order = p + 1
        print(f"[+] Curve order (p=3 mod 4): {order}")
    else:
        # p = 1 mod 4. For y^2 = x^3 + x, #E = p + 1 - 2a where p = a^2 + b^2
        # (Gaussian integer factorization)
        # But let's try: the order should be near p+1 (Hasse bound: |#E - p - 1| <= 2*sqrt(p))
        # Try to find order by testing multiples of G
        print("[*] p = 1 mod 4, computing order via Hasse bound + factor search...")

        # Hasse bound: p + 1 - 2*sqrt(p) <= #E <= p + 1 + 2*sqrt(p)
        sqrtp = math.isqrt(p)
        lo = p + 1 - 2 * sqrtp
        hi = p + 1 + 2 * sqrtp
        print(f"[*] Hasse bound: [{lo}, {hi}]")
        print(f"[*] Range size: {hi - lo}")

        # The trace t satisfies #E = p + 1 - t, and for y^2 = x^3 + x with p = 1 mod 4,
        # we can write p = a^2 + b^2 (sum of two squares since p = 1 mod 4)
        # and t = +-2a (choosing a appropriately)

        # Find a, b such that p = a^2 + b^2
        # Using Cornacchia's algorithm
        def cornacchia(d, p):
            """Find x, y such that x^2 + d*y^2 = p."""
            # Find square root of -d mod p
            # For d=1: sqrt(-1) mod p
            # Since p = 1 mod 4, -1 is a QR mod p
            r = pow(2, (p - 1) // 4, p)  # Try this as sqrt(-1)
            if (r * r) % p != (p - 1):
                # Try other method
                for g in range(2, 100):
                    r = pow(g, (p - 1) // 4, p)
                    if (r * r) % p == (p - 1):
                        break

            assert (r * r) % p == (p - 1), "Failed to find sqrt(-1)"

            # Euclidean algorithm
            a, b = p, r
            limit = math.isqrt(p)
            while b > limit:
                a, b = b, a % b

            s_sq = p - b * b
            if s_sq % d != 0:
                return None
            s = math.isqrt(s_sq // d)
            if s * s * d + b * b != p:
                return None
            return b, s

        result = cornacchia(1, p)
        if result:
            aa, bb = result
            print(f"[+] p = {aa}^2 + {bb}^2 = {aa*aa + bb*bb}")
            # t = +-2a where a = aa (or bb)
            # Need to determine sign: #E = p + 1 - t
            for sign in [1, -1]:
                for val in [aa, bb]:
                    t = sign * 2 * val
                    candidate_order = p + 1 - t
                    # Verify: candidate_order * G should be identity
                    test = point_mul(candidate_order, G)
                    if test is None:
                        order = candidate_order
                        print(f"[+] Curve order: {order} (t = {t})")
                        break
                if order:
                    break

        if order is None:
            # Brute force search in Hasse range
            print("[*] Brute-force searching for order...")
            # Compute lo * G, then add G repeatedly
            current = point_mul(lo, G)
            for candidate in range(lo, hi + 1):
                if current is None:
                    order = candidate
                    print(f"[+] Found order: {order}")
                    break
                current = point_add(current, G)

    if order is None:
        print("[!] Could not determine curve order")
        sys.exit(1)

    # Factor the order
    print(f"[*] Factoring order {order}...")
    factors = factor_trial(order)
    print(f"[+] Factors: {factors}")

    # Check if all factors are small enough for BSGS
    product = 1
    for prime, exp in factors.items():
        product *= prime ** exp
    assert product == order, "Incomplete factorization!"

    # Pohlig-Hellman
    print("[*] Running Pohlig-Hellman...")
    k = pohlig_hellman(G, Q, order, factors)

    if k is not None:
        # Verify
        verify = point_mul(k, G)
        if verify == Q:
            print(f"\n[+] PRIVATE KEY: {k}")
            print(f"[+] Verification: k*G == Q ✓")
        else:
            print(f"[!] Verification failed: k*G = {verify}, Q = {Q}")
            # Try order - k
            k2 = order - k
            verify2 = point_mul(k2, G)
            if verify2 == Q:
                print(f"[+] PRIVATE KEY (adjusted): {k2}")
                k = k2
    else:
        print("[!] Pohlig-Hellman failed")


if __name__ == "__main__":
    main()
