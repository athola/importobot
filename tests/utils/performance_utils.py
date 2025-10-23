"""Dynamic performance threshold utility for adaptive performance testing.

Adjusts performance expectations based on system resources to make tests
more reliable across different CI environments and machine configurations.
"""

import os
import time


class SystemResources:
    """Detect current system resource availability."""

    def __init__(self) -> None:
        """Initialize system resource detector."""
        self._cpu_count = os.cpu_count() or 1
        self._load_average = self._get_load_average()
        self._memory_info = self._get_memory_info()

    def _get_load_average(self) -> float:
        """Get system load average."""
        try:
            # Unix-like systems
            return os.getloadavg()[0] / self._cpu_count
        except (OSError, AttributeError):
            # Windows or default path
            return 0.5  # Conservative assumption

    def _get_memory_info(self) -> dict[str, float]:
        """Get basic memory information."""
        try:
            # Try to read from /proc/meminfo on Linux
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", encoding="utf-8") as f:
                    meminfo = f.read()

                total_kb = 0
                available_kb = 0

                for line in meminfo.split("\n"):
                    if "MemTotal:" in line:
                        total_kb = int(line.split()[1])
                    elif "MemAvailable:" in line:
                        available_kb = int(line.split()[1])

                if total_kb > 0:
                    usage = 1 - (available_kb / total_kb) if total_kb > 0 else 0.5
                    return {
                        "total_bytes": total_kb * 1024,
                        "available_bytes": available_kb * 1024,
                        "usage_ratio": usage,
                    }
        except Exception:
            pass

        # Default assumptions
        return {
            "total_bytes": 8 * 1024 * 1024 * 1024,  # 8GB
            "available_bytes": 4 * 1024 * 1024 * 1024,  # 4GB
            "usage_ratio": 0.5,
        }

    @property
    def cpu_count(self) -> int:
        """Get CPU count."""
        return self._cpu_count

    @property
    def load_ratio(self) -> float:
        """Load per CPU core."""
        return self._load_average

    @property
    def memory_usage_ratio(self) -> float:
        """Memory usage ratio (0-1)."""
        return self._memory_info["usage_ratio"]

    @property
    def is_under_load(self) -> bool:
        """System appears to be under significant load."""
        return self.load_ratio > 1.0 or self.memory_usage_ratio > 0.8

    @property
    def performance_factor(self) -> float:
        """Performance multiplier based on system state."""
        load_factor = max(0.3, 1.0 / (1.0 + self.load_ratio))
        memory_factor = max(0.5, 1.0 - self.memory_usage_ratio * 0.5)
        return load_factor * memory_factor


class AdaptiveThresholds:
    """Dynamic performance thresholds that adapt to system resources."""

    def __init__(self) -> None:
        """Initialize adaptive thresholds with system measurements."""
        self.system = SystemResources()
        self.baseline_overhead = self._measure_baseline_overhead()

    def _measure_baseline_overhead(self) -> float:
        """Measure baseline timing overhead for this system."""
        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            # Simple operation similar to telemetry overhead
            now = time.time()
            _ = now > 0

        elapsed = time.perf_counter() - start
        return elapsed / iterations

    def adjust_threshold(
        self,
        base_threshold: float,
        complexity_factor: float = 1.0,
        min_multiplier: float = 0.5,
        max_multiplier: float = 5.0,
    ) -> float:
        """Adjust a base threshold based on system performance."""
        # Start with baseline adjustment
        adjusted = base_threshold * max(1.0, self.baseline_overhead * 1000)

        # Apply system performance factor
        performance_multiplier = 1.0 / max(0.2, self.system.performance_factor)

        # Apply complexity factor
        total_multiplier = performance_multiplier * complexity_factor

        # Clamp to reasonable bounds
        total_multiplier = max(min_multiplier, min(max_multiplier, total_multiplier))

        return adjusted * total_multiplier

    def get_telemetry_threshold(self, enabled: bool = False) -> float:
        """Get appropriate threshold for telemetry overhead tests."""
        if enabled:
            # Enabled telemetry has more work to do
            base = 1e-5  # 10 microseconds
            complexity = 3.0  # More complex operations, be more lenient
        else:
            # Disabled telemetry should be very fast
            base = 5e-6  # 5 microseconds
            complexity = 1.0

        return self.adjust_threshold(
            base, complexity, min_multiplier=1.0, max_multiplier=10.0
        )

    def get_operation_threshold(self, base_ms: float) -> float:
        """Get threshold for general operations (in milliseconds)."""
        base_seconds = base_ms / 1000.0
        return self.adjust_threshold(base_seconds) * 1000.0

    def get_throughput_threshold(self, base_ops_per_sec: float) -> float:
        """Get minimum throughput threshold (operations per second)."""
        # Reduce expectations based on system load and logging overhead
        reduction_factor = self.system.performance_factor * 0.05  # Be very conservative
        return base_ops_per_sec * max(0.05, reduction_factor)


# Global instance for reuse
_global_thresholds: AdaptiveThresholds | None = None


def get_adaptive_thresholds() -> AdaptiveThresholds:
    """Get the global adaptive thresholds instance."""
    global _global_thresholds  # pylint: disable=global-statement
    if _global_thresholds is None:
        _global_thresholds = AdaptiveThresholds()
    return _global_thresholds


def adaptive_threshold(base_threshold: float, complexity_factor: float = 1.0) -> float:
    """Get an adjusted threshold based on system performance."""
    return get_adaptive_thresholds().adjust_threshold(base_threshold, complexity_factor)


def system_info() -> dict[str, object]:
    """Get system resource information for debugging."""
    system = SystemResources()
    return {
        "cpu_count": system.cpu_count,
        "load_ratio": system.load_ratio,
        "memory_usage_ratio": system.memory_usage_ratio,
        "performance_factor": system.performance_factor,
        "is_under_load": system.is_under_load,
    }
