#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <immintrin.h>

double tempo_em_milissegundos(struct timespec inicio, struct timespec fim)
{
    double segundos = (double)(fim.tv_sec - inicio.tv_sec);
    double nanossegundos = (double)(fim.tv_nsec - inicio.tv_nsec);

    return segundos * 1000.0 + nanossegundos / 1e6;
}

double distancia_avx(const double * restrict a,
                     const double * restrict b,
                     size_t n)
{
    /*
     * OTIMIZACAO 1:
     * Uso de AVX2 para processar quatro valores double simultaneamente.
     *
     * Um registrador __m256d possui 256 bits:
     *
     *      256 / 64 = 4 doubles
     *
     * Em vez de processar um elemento por iteracao, processamos
     * quatro elementos de cada vetor simultaneamente.
     */

    /*
     * OTIMIZACAO 2:
     * Uso de quatro acumuladores independentes.
     *
     * Um unico acumulador criaria uma dependencia entre iteracoes:
     *
     *      acc -> acc -> acc -> acc ...
     *
     * Utilizando quatro acumuladores independentes, o processador
     * pode executar varias operacoes simultaneamente, explorando
     * paralelismo em nivel de instrucoes (ILP).
     *
     * Como cada acumulador processa quatro doubles, cada iteracao
     * do laco principal processa 16 elementos.
     */
    __m256d acc0 = _mm256_setzero_pd();
    __m256d acc1 = _mm256_setzero_pd();
    __m256d acc2 = _mm256_setzero_pd();
    __m256d acc3 = _mm256_setzero_pd();

    size_t i = 0;

    for (; i + 15 < n; i += 16) {

        /*
         * OTIMIZACAO 3:
         * Loads alinhados de 256 bits.
         *
         * Os vetores foram alocados em enderecos multiplos de
         * 32 bytes. Assim podemos utilizar _mm256_load_pd(),
         * que realiza uma leitura alinhada de quatro doubles.
         */

        __m256d a0 = _mm256_load_pd(&a[i]);
        __m256d b0 = _mm256_load_pd(&b[i]);

        __m256d a1 = _mm256_load_pd(&a[i + 4]);
        __m256d b1 = _mm256_load_pd(&b[i + 4]);

        __m256d a2 = _mm256_load_pd(&a[i + 8]);
        __m256d b2 = _mm256_load_pd(&b[i + 8]);

        __m256d a3 = _mm256_load_pd(&a[i + 12]);
        __m256d b3 = _mm256_load_pd(&b[i + 12]);

        /*
         * Calcula simultaneamente quatro diferencas.
         */
        __m256d d0 = _mm256_sub_pd(a0, b0);
        __m256d d1 = _mm256_sub_pd(a1, b1);
        __m256d d2 = _mm256_sub_pd(a2, b2);
        __m256d d3 = _mm256_sub_pd(a3, b3);

        /*
         * OTIMIZACAO 4:
         * Uso de FMA - Fused Multiply Add.
         *
         * A operacao:
         *
         *      acc = acc + d * d
         *
         * e realizada por uma unica instrucao FMA:
         *
         *      _mm256_fmadd_pd(d, d, acc)
         *
         * Isso reduz o numero de instrucoes e permite ao processador
         * executar multiplicacao e soma de forma combinada.
         */
        acc0 = _mm256_fmadd_pd(d0, d0, acc0);
        acc1 = _mm256_fmadd_pd(d1, d1, acc1);
        acc2 = _mm256_fmadd_pd(d2, d2, acc2);
        acc3 = _mm256_fmadd_pd(d3, d3, acc3);
    }

    /*
     * OTIMIZACAO 5:
     * Reducao dos quatro acumuladores vetoriais.
     *
     * Primeiro somamos os quatro acumuladores AVX.
     * O resultado ainda contem quatro valores double.
     */
    __m256d soma01 = _mm256_add_pd(acc0, acc1);
    __m256d soma23 = _mm256_add_pd(acc2, acc3);
    __m256d soma_vetorial = _mm256_add_pd(soma01, soma23);

    /*
     * Reducao horizontal dos quatro valores existentes no
     * registrador AVX para produzir um unico valor escalar.
     */
    __m128d parte_baixa = _mm256_castpd256_pd128(soma_vetorial);
    __m128d parte_alta =
        _mm256_extractf128_pd(soma_vetorial, 1);

    __m128d soma128 =
        _mm_add_pd(parte_baixa, parte_alta);

    __m128d trocado =
        _mm_shuffle_pd(soma128, soma128, 0x1);

    soma128 =
        _mm_add_sd(soma128, trocado);

    double soma = _mm_cvtsd_f64(soma128);

    /*
     * OTIMIZACAO 6:
     * Tratamento escalar apenas dos elementos restantes.
     *
     * Como o laco AVX processa blocos de 16 elementos,
     * pode haver de 0 a 15 elementos restantes quando n nao
     * for multiplo de 16.
     *
     * Esses elementos sao processados pela implementacao escalar.
     */
    for (; i < n; i++) {
        double diferenca = a[i] - b[i];
        soma += diferenca * diferenca;
    }

    return sqrt(soma);
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

    double *a = NULL;
    double *b = NULL;

    /*
     * OTIMIZACAO 7:
     * Alocacao alinhada em 32 bytes.
     *
     * Registradores AVX possuem 256 bits = 32 bytes.
     *
     * Garantindo que o inicio dos vetores esteja alinhado em
     * 32 bytes podemos utilizar _mm256_load_pd() nos acessos
     * vetoriais.
     */
    if (posix_memalign((void **)&a, 32, n * sizeof(double)) != 0 ||
        posix_memalign((void **)&b, 32, n * sizeof(double)) != 0) {

        fprintf(stderr, "Erro de alocacao de memoria.\n");
        free(a);
        free(b);
        return EXIT_FAILURE;
    }

    /*
     * Inicializacao fora da regiao cronometrada.
     */
    for (size_t i = 0; i < n; i++) {
        a[i] = (double)i;
        b[i] = (double)(n - i);
    }

    struct timespec inicio;
    struct timespec fim_tempo;

    clock_gettime(CLOCK_MONOTONIC, &inicio);

    double resultado = distancia_avx(a, b, n);

    clock_gettime(CLOCK_MONOTONIC, &fim_tempo);

    double tempo =
        tempo_em_milissegundos(inicio, fim_tempo);

    /*
     * Mantem o resultado observavel para impedir que o
     * compilador elimine o calculo por considerá-lo inutil.
     */
    if (resultado < 0.0) {
        fprintf(stderr, "%f\n", resultado);
    }

    printf("gerson,%zu,%.6f\n", n, tempo);

    free(a);
    free(b);

    return EXIT_SUCCESS;
}
