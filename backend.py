"""
Backend selection — the ONE place that knows about hardware/simulators.

Keep every framework/hardware choice here. Local development uses a simulator;
on QCentroid Launchpad you swap the backend with a single change (env var or
argument) without touching the QAOA logic.

Usage:
    from backend import get_backend
    dev = get_backend(framework="pennylane", name="default.qubit", wires=10)
"""
import os


def get_backend(framework=None, name=None, wires=None, shots=None):
    """Return a backend handle for the chosen framework.

    framework : "pennylane" or "qiskit"  (defaults to env QAOA_FRAMEWORK or pennylane)
    name      : device/backend name. Defaults below pick a local simulator.
    wires     : number of qubits (PennyLane needs this up front).
    shots     : measurement shots (None = analytic/statevector where supported).
    """
    framework = framework or os.environ.get("QAOA_FRAMEWORK", "pennylane")

    if framework == "pennylane":
        import pennylane as qml
        name = name or os.environ.get("QAOA_DEVICE", "default.qubit")
        # On QCentroid GPU: try "lightning.gpu"; locally "lightning.qubit" or "default.qubit".
        return qml.device(name, wires=wires, shots=shots)

    if framework == "qiskit":
        # Local Aer simulator. On QCentroid, point this at the provided backend.
        name = name or os.environ.get("QAOA_DEVICE", "aer_simulator")
        try:
            from qiskit_aer import AerSimulator
            return AerSimulator()
        except ImportError:
            from qiskit_aer import Aer
            return Aer.get_backend(name)

    raise ValueError(f"Unknown framework: {framework}")
