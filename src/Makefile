CC = gcc

CFLAGS_NAIVE = -O2 -Wall -Wextra
CFLAGS_OTIMIZADA = -O2 -Wall -Wextra -mavx2 -mfma

LDLIBS = -lm

all: distancia_naive distancia_avx

distancia_naive: distancia_naive.c
	$(CC) $(CFLAGS_NAIVE) $< -o $@ $(LDLIBS)

distancia_avx: distancia_avx.c
	$(CC) $(CFLAGS_OTIMIZADA) $< -o $@ $(LDLIBS)

clean:
	rm -f distancia_naive distancia_avx

.PHONY: all clean
