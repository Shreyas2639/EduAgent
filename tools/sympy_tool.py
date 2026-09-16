import sympy as sp

def solve_math(expression: str) -> str:
    try:
        x, y, z, n = sp.symbols('x y z n')
        if '=' in expression:
            parts = expression.split('=')
            lhs = sp.sympify(parts[0].strip())
            rhs = sp.sympify(parts[1].strip())
            solutions = sp.solve(lhs - rhs, x)
            return f"Solving {expression}:\nx = {solutions}"
        expr = sp.sympify(expression)
        simplified = sp.simplify(expr)
        result = f"Expression: {expression}\nSimplified: {simplified}\n"
        if expr.free_symbols:
            derivative = sp.diff(expr, x)
            result += f"Derivative (d/dx): {derivative}\n"
        return result
    except Exception as e:
        return f"Could not solve: {expression}. Error: {str(e)}"
