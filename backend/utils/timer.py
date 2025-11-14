import time

def measure(label: str):
    start = time.perf_counter()

    def end():
        duration = (time.perf_counter() - start) * 1000  # ms
        print(f"⏱️ {label}: {duration:.2f} ms")

    return end
