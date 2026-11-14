"""Простой консольный калькулятор на Python."""

import math


def main():
    print("Простой калькулятор")
    while True:
        try:
            first = float(input("Введите первое число: "))
            second = float(input("Введите второе число: "))
            if not math.isfinite(first) or not math.isfinite(second):
                print("Ошибка: введите конечные числа.")
                continue
        except ValueError:
            print("Ошибка: введите число, используя точку для дробной части.")
            continue

        operation = input("Выберите операцию (+, -, *, /): ").strip()
        if operation == "+":
            result = first + second
        elif operation == "-":
            result = first - second
        elif operation == "*":
            result = first * second
        elif operation == "/":
            if second == 0:
                print("Ошибка: деление на ноль невозможно.")
                continue
            result = first / second
        else:
            print("Ошибка: неизвестная операция.")
            continue

        if math.isfinite(result):
            print(f"Результат: {result:g}")
        else:
            print("Ошибка: результат слишком велик.")

        while True:
            answer = input("Следующее вычисление? (д/н): ").strip().lower()
            if answer in ("д", "н"):
                break
            print("Ошибка: введите д или н.")
        if answer == "н":
            print("Работа завершена.")
            break


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nРабота завершена.")
