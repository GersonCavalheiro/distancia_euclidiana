#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

double distancia(const double *a, const double *b, size_t n)
{
    double soma = 0.0;

    for (size_t i = 0; i < n; i++) {
        double diferenca = a[i] - b[i];
        soma += diferenca * diferenca;
    }

    return sqrt(soma);
}

double tempo_em_milissegundos(struct timespec inicio, struct timespec fim)
{
    double segundos = (double)(fim.tv_sec - inicio.tv_sec);
    double nanossegundos = (double)(fim.tv_nsec - inicio.tv_nsec);

    return segundos * 1000.0 + nanossegundos / 1e6;
}

int main(int argc, char *argv[])
{
    if (argc != 2) {
        fprintf(stderr, "Uso: %s <tamanho>\n", argv[0]);
        return EXIT_FAILURE;
    }

    char *fim;
    unsigned long long valor = strtoull(argv[1], &fim, 10);

    if (*fim != '\0' || valor == 0) {
        fprintf(stderr, "Tamanho invalido.\n");
        return EXIT_FAILURE;
    }

    size_t n = (size_t)valor;

    double *a = malloc(n * sizeof(double));
    double *b = malloc(n * sizeof(double));

    if (a == NULL || b == NULL) {
        fprintf(stderr, "Erro de alocacao de memoria.\n");
        free(a);
        free(b);
        return EXIT_FAILURE;
    }

    for (size_t i = 0; i < n; i++) {
        a[i] = (double)i;
        b[i] = (double)(n - i);
    }

    struct timespec inicio, fim_tempo;

    clock_gettime(CLOCK_MONOTONIC, &inicio);

    double resultado = distancia(a, b, n);

    clock_gettime(CLOCK_MONOTONIC, &fim_tempo);

    double tempo = tempo_em_milissegundos(inicio, fim_tempo);

    if (resultado < 0.0) {
        fprintf(stderr, "%f\n", resultado);
    }

    printf("gerson,%zu,%.6f\n", n, tempo);

    free(a);
    free(b);

    return EXIT_SUCCESS;
}
