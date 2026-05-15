from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from quantum_circuit_drawer import draw_quantum_circuit

qr1 = QuantumRegister(2, name="qchannel(1)")
qr2 = QuantumRegister(1, name="qchannel(2)")
cr = ClassicalRegister(3, name="classic")

qc = QuantumCircuit(qr1, qr2, cr, name="Circuit")

qc.h(0)
qc.barrier()

qc.x(qr1[0])
qc.x(qr1[1])
qc.barrier([1, 2])
qc.x(qr2[0])
qc.cx(qr1[0], qr1[1])

qc.barrier()

qc.measure(qr1[0], 0)
qc.measure(qr1[1], 1)
qc.measure(qr2[0], 2)

# qc.draw("mpl")
draw_quantum_circuit(qc)
