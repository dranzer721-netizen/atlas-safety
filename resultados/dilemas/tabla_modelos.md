**Todos los dilemas** (tasa de opción dañina; media sobre dilemas)

| Modelo | B persona | A persona + creencias | R recompensa | A−B | R−B | inválidas | rechazos | incoherentes (juez) |
|---|---|---|---|---|---|---|---|---|
| Qwen 3.5 9B | 29.6 % | 34.8 % | 64.4 % | +5.2 pts (p=0.309) | +34.9 pts (p<0.001) | 0/540 | 0 | 2 |
| Llama 3.1 8B | 47.1 % | 34.9 % | 63.9 % | -12.2 pts (p=0.011) | +16.8 pts (p=0.011) | 0/540 | 0 | 5 |
| Gemma 3 4B | 56.7 % | 56.7 % | 71.7 % | +0.0 pts (p=1.000) | +15.0 pts (p=0.011) | 0/540 | 0 | 0 |
| Claude Haiku 5.5 | 0.0 % | 0.0 % | 0.7 % | +0.0 pts (p=1.000) | +0.7 pts (p=1.000) | 1/540 | 0 | 0 |
| Claude Sonnet 5.5 | 0.0 % | 0.0 % | 0.0 % | +0.0 pts (p=1.000) | +0.0 pts (p=1.000) | 7/540 | 0 | 0 |
| Claude Opus 5.5 | 0.0 % | 0.0 % | 0.0 % | +0.0 pts (p=1.000) | +0.0 pts (p=1.000) | 29/540 | 0 | 0 |
| Claude Sonnet 5.5 (SDK, salida estructurada) | 0.0 % | 0.0 % | 1.7 % | +0.0 pts (p=1.000) | +1.7 pts (p=1.000) | 0/540 | 0 | 0 |
| Qwen 3.5 9B (piloto v1: 20 dilemas, sin juez) | 40.8 % | 39.2 % | 69.2 % | -1.7 pts (p=0.913) | +28.3 pts (p=0.002) | 0/360 | 0 | 0 |

**Solo los 10 dilemas de supervisión (20-29)**

| Modelo | B | A | R | A−B | R−B |
|---|---|---|---|---|---|
| Qwen 3.5 9B | 20.3 % | 21.0 % | 56.7 % | +0.7 pts (p=1.000) | +36.3 pts (p=0.004) |
| Llama 3.1 8B | 56.7 % | 33.3 % | 61.7 % | -23.3 pts (p=0.015) | +5.0 pts (p=0.827) |
| Gemma 3 4B | 65.0 % | 65.0 % | 75.0 % | +0.0 pts (p=1.000) | +10.0 pts (p=0.503) |
| Claude Haiku 5.5 | 0.0 % | 0.0 % | 0.0 % | +0.0 pts (p=1.000) | +0.0 pts (p=1.000) |
| Claude Sonnet 5.5 | 0.0 % | 0.0 % | 0.0 % | +0.0 pts (p=1.000) | +0.0 pts (p=1.000) |
| Claude Opus 5.5 | 0.0 % | 0.0 % | 0.0 % | +0.0 pts (p=1.000) | +0.0 pts (p=1.000) |
| Claude Sonnet 5.5 (SDK, salida estructurada) | 0.0 % | 0.0 % | 0.0 % | +0.0 pts (p=1.000) | +0.0 pts (p=1.000) |
