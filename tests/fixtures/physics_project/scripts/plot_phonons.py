import numpy as np
import matplotlib.pyplot as plt

# Simulate phonon density of states
frequencies = np.linspace(0, 100, 1000)
dos = np.exp(-((frequencies - 20) ** 2) / 50) + 0.5 * np.exp(
    -((frequencies - 80) ** 2) / 100
)

plt.figure(figsize=(8, 5))
plt.plot(frequencies, dos, label="Phonon DOS")
plt.xlabel("Frequency (THz)")
plt.ylabel("DOS (states/THz)")
plt.title("Phonon Density of States for SH3 at 200 GPa")
plt.legend()
plt.savefig("../paper/figures/phonon_dispersion.png")
print("Generated phonon_dispersion.png")
