def run_custom_checker(t_obj, r_obj):
    try:
        # ----------------------------------------------------
        # Read input
        # ----------------------------------------------------
        with open(t_obj.testcase_input_path) as f:
            data = f.read().split()

        if len(data) < 2:
            r_obj.result = False
            r_obj.score = 0.0
            r_obj.message = "Invalid input"
            return

        it = iter(data)

        n = int(next(it))
        target = int(next(it))

        a = [int(next(it)) for _ in range(n)]

        # ----------------------------------------------------
        # Read contestant output
        # ----------------------------------------------------
        with open(t_obj.testcase_output_path) as f:
            tokens = f.read().strip().split()

        # Output must contain either:
        # - one integer: -1
        # - two integers: i j
        if not tokens:
            r_obj.result = False
            r_obj.score = 0.0
            r_obj.message = "No output"
            return

        # ----------------------------------------------------
        # Compute the first valid pair independently
        # ----------------------------------------------------
        expected_i = -1
        expected_j = -1

        for i in range(n):
            for j in range(i + 1, n):
                if a[i] + a[j] == target:
                    expected_i = i
                    expected_j = j
                    break

            if expected_i != -1:
                break

        # ----------------------------------------------------
        # Expected output = -1
        # ----------------------------------------------------
        if expected_i == -1:
            if len(tokens) != 1:
                r_obj.result = False
                r_obj.score = 0.0
                r_obj.message = "Expected -1"
                return

            if tokens[0] == "-1":
                r_obj.result = True
                r_obj.score = 1.0
                r_obj.message = "Success"
            else:
                r_obj.result = False
                r_obj.score = 0.0
                r_obj.message = "Expected -1"

            return

        # ----------------------------------------------------
        # Expected output = pair of indices
        # ----------------------------------------------------
        if len(tokens) != 2:
            r_obj.result = False
            r_obj.score = 0.0
            r_obj.message = "Expected two indices"
            return

        try:
            i = int(tokens[0])
            j = int(tokens[1])
        except ValueError:
            r_obj.result = False
            r_obj.score = 0.0
            r_obj.message = "Indices must be integers"
            return

        # Check index bounds
        if i < 0 or i >= n or j < 0 or j >= n:
            r_obj.result = False
            r_obj.score = 0.0
            r_obj.message = "Index out of bounds"
            return

        # Check ordering
        if i >= j:
            r_obj.result = False
            r_obj.score = 0.0
            r_obj.message = "Require i < j"
            return

        # Check whether pair actually satisfies target
        if a[i] + a[j] != target:
            r_obj.result = False
            r_obj.score = 0.0
            r_obj.message = "Selected indices do not sum to target"
            return

        # Problem asks for the FIRST valid pair.
        if i != expected_i or j != expected_j:
            r_obj.result = False
            r_obj.score = 0.0
            r_obj.message = (
                f"Expected first pair ({expected_i}, {expected_j}), "
                f"got ({i}, {j})"
            )
            return

        # Correct answer
        r_obj.result = True
        r_obj.score = 1.0
        r_obj.message = "Success"

    except Exception as e:
        r_obj.result = False
        r_obj.score = 0.0
        r_obj.message = f"Checker error: {str(e)}"