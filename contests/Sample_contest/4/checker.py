def run_custom_checker(t_obj, r_obj):
    try:
        # ----------------------------------------------------
        # Read input
        # ----------------------------------------------------
        with open(t_obj.testcase_input_path) as f:
            data = f.read().split()

        it = iter(data)

        t = int(next(it))

        cases = []

        for _ in range(t):
            n = int(next(it))
            k = int(next(it))
            x = int(next(it))

            a = [int(next(it)) for _ in range(n)]

            cases.append((n, k, x, a))

        # ----------------------------------------------------
        # Read contestant output
        # ----------------------------------------------------
        with open(t_obj.testcase_output_path) as f:
            output = f.read().split()

        if len(output) != t:
            r_obj.result = False
            r_obj.score = 0.0
            r_obj.message = (
                f"Expected {t} output values, got {len(output)}"
            )
            return

        contestant = []

        for token in output:
            try:
                contestant.append(int(token))
            except ValueError:
                r_obj.result = False
                r_obj.score = 0.0
                r_obj.message = "Output contains a non-integer value"
                return

        # ----------------------------------------------------
        # Efficiently calculate the answer.
        #
        # b = a repeated k times.
        #
        # For a starting position l, let:
        #
        #     len = n*k - l + 1
        #
        # be the suffix length.
        #
        # The suffix consists of:
        #   full = len // n complete copies of a
        #   rem  = len % n elements from the end of a
        #
        # suffix_sum =
        #   full * sum(a)
        #   + sum of the last rem elements of a
        #
        # Since all a[i] are positive, suffix_sum is monotonically
        # decreasing as l increases.
        # ----------------------------------------------------

        expected = []

        for n, k, x, a in cases:
            total_a = sum(a)
            total_b = total_a * k

            # Even the complete array is insufficient.
            if total_b < x:
                expected.append(0)
                continue

            # Prefix sums allow O(log n) suffix queries.
            prefix = [0] * (n + 1)

            for i in range(n):
                prefix[i + 1] = prefix[i] + a[i]

            total_positions = n * k

            def suffix_sum(l):
                """
                l is 1-indexed.

                Returns:
                    b[l] + b[l+1] + ... + b[n*k]
                """
                length = total_positions - l + 1

                full = length // n
                rem = length % n

                # Last rem elements of a.
                remainder_sum = prefix[n] - prefix[n - rem]

                return full * total_a + remainder_sum

            # Find the largest valid l.
            lo = 1
            hi = total_positions
            answer = 0

            while lo <= hi:
                mid = (lo + hi) // 2

                if suffix_sum(mid) >= x:
                    answer = mid
                    lo = mid + 1
                else:
                    hi = mid - 1

            # Valid positions are 1 ... answer.
            expected.append(answer)

        # ----------------------------------------------------
        # Compare
        # ----------------------------------------------------
        for i in range(t):
            if contestant[i] != expected[i]:
                r_obj.result = False
                r_obj.score = 0.0
                r_obj.message = (
                    f"Wrong answer at test case {i + 1}: "
                    f"expected {expected[i]}, got {contestant[i]}"
                )
                return

        r_obj.result = True
        r_obj.score = 1.0
        r_obj.message = "Success"

    except Exception as e:
        r_obj.result = False
        r_obj.score = 0.0
        r_obj.message = f"Checker error: {str(e)}"