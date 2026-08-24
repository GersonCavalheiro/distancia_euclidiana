#!/usr/bin/env python3

import argparse
import csv
import math
import random
import shutil
import statistics
import sys

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


# ============================================================
# Configuração
# ============================================================

NUM_BOOTSTRAP_PADRAO = 10000
NUM_PERMUTACOES_PADRAO = 10000
SEED_PADRAO = 12345


# ============================================================
# Utilidades
# ============================================================

def anunciar(texto):
    print()
    print("=" * 72)
    print(texto)
    print("=" * 72)


def escapar_latex(texto):
    substituicoes = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}"
    }

    resultado = str(texto)

    for original, substituto in substituicoes.items():
        resultado = resultado.replace(
            original,
            substituto
        )

    return resultado


# ============================================================
# Diretório de registro
# ============================================================

def criar_diretorio_registro(arquivo_coleta):
    agora = datetime.now()

    nome_base = agora.strftime(
        "Registro-Comparacao-%Y%m%d-%H%M%S"
    )

    diretorio = Path(nome_base)

    contador = 1

    while diretorio.exists():
        diretorio = Path(
            f"{nome_base}-{contador}"
        )
        contador += 1

    diretorio.mkdir()

    shutil.copy2(
        arquivo_coleta,
        diretorio / "coleta.csv"
    )

    try:
        shutil.copy2(
            Path(__file__).resolve(),
            diretorio / "comparacao.py"
        )
    except Exception:
        pass

    return diretorio, agora


# ============================================================
# Leitura dos dados
# ============================================================

def ler_dados(arquivo_csv):
    dados = []

    with open(
        arquivo_csv,
        "r",
        encoding="utf-8"
    ) as arquivo:

        leitor = csv.DictReader(arquivo)

        obrigatorios = {
            "rodada",
            "ordem",
            "executavel",
            "nome",
            "tamanho",
            "tempo_ms"
        }

        if leitor.fieldnames is None:
            raise ValueError(
                "O arquivo CSV não possui cabeçalho."
            )

        faltantes = obrigatorios - set(
            leitor.fieldnames
        )

        if faltantes:
            raise ValueError(
                "Campos ausentes: "
                + ", ".join(sorted(faltantes))
            )

        for linha in leitor:
            dados.append({
                "rodada": int(linha["rodada"]),
                "ordem": int(linha["ordem"]),
                "executavel": linha["executavel"],
                "nome": linha["nome"],
                "tamanho": int(linha["tamanho"]),
                "tempo_ms": float(linha["tempo_ms"])
            })

    return dados


# ============================================================
# Formação dos pares
# ============================================================

def formar_pares(
    dados,
    referencia,
    comparada,
    tamanhos
):
    """
    Para cada tamanho e rodada, procura:

        referencia
        comparada

    e forma um par de observações.

    Pares incompletos são informados e ignorados.
    Duplicatas são tratadas como erro experimental.
    """

    indice = {}

    for registro in dados:

        if registro["tamanho"] not in tamanhos:
            continue

        if registro["executavel"] not in {
            referencia,
            comparada
        }:
            continue

        chave = (
            registro["tamanho"],
            registro["rodada"],
            registro["executavel"]
        )

        if chave in indice:
            raise ValueError(
                "Observação duplicada para "
                f"tamanho={registro['tamanho']}, "
                f"rodada={registro['rodada']}, "
                f"executável={registro['executavel']}."
            )

        indice[chave] = registro

    pares = {}
    avisos = []

    rodadas_por_tamanho = {}

    for tamanho, rodada, executavel in indice:
        rodadas_por_tamanho.setdefault(
            tamanho,
            set()
        ).add(rodada)

    for tamanho in sorted(tamanhos):

        pares[tamanho] = []

        rodadas = sorted(
            rodadas_por_tamanho.get(
                tamanho,
                set()
            )
        )

        for rodada in rodadas:

            chave_ref = (
                tamanho,
                rodada,
                referencia
            )

            chave_cmp = (
                tamanho,
                rodada,
                comparada
            )

            existe_ref = chave_ref in indice
            existe_cmp = chave_cmp in indice

            if not (
                existe_ref
                and existe_cmp
            ):

                avisos.append(
                    f"Par incompleto: tamanho={tamanho}, "
                    f"rodada={rodada}; "
                    f"referência={'OK' if existe_ref else 'AUSENTE'}, "
                    f"comparada={'OK' if existe_cmp else 'AUSENTE'}."
                )

                continue

            ref = indice[chave_ref]
            cmp_ = indice[chave_cmp]

            tempo_ref = ref["tempo_ms"]
            tempo_cmp = cmp_["tempo_ms"]

            diferenca = (
                tempo_ref
                - tempo_cmp
            )

            speedup = (
                tempo_ref / tempo_cmp
                if tempo_cmp != 0
                else math.inf
            )

            pares[tamanho].append({
                "rodada": rodada,

                "tempo_referencia_ms":
                    tempo_ref,

                "tempo_comparada_ms":
                    tempo_cmp,

                "diferenca_ms":
                    diferenca,

                "speedup":
                    speedup
            })

    return pares, avisos


# ============================================================
# Funções para distribuição t
# ============================================================

def _betacf(a, b, x):
    """
    Fração contínua para cálculo da função beta incompleta.
    """

    MAXIT = 200
    EPS = 3.0e-14
    FPMIN = 1.0e-300

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0

    c = 1.0

    d = 1.0 - qab * x / qap

    if abs(d) < FPMIN:
        d = FPMIN

    d = 1.0 / d
    h = d

    for m in range(1, MAXIT + 1):

        m2 = 2 * m

        aa = (
            m
            * (b - m)
            * x
            / (
                (qam + m2)
                * (a + m2)
            )
        )

        d = 1.0 + aa * d

        if abs(d) < FPMIN:
            d = FPMIN

        c = 1.0 + aa / c

        if abs(c) < FPMIN:
            c = FPMIN

        d = 1.0 / d
        h *= d * c

        aa = (
            -(
                (a + m)
                * (qab + m)
                * x
            )
            / (
                (a + m2)
                * (qap + m2)
            )
        )

        d = 1.0 + aa * d

        if abs(d) < FPMIN:
            d = FPMIN

        c = 1.0 + aa / c

        if abs(c) < FPMIN:
            c = FPMIN

        d = 1.0 / d

        delta = d * c
        h *= delta

        if abs(delta - 1.0) < EPS:
            break

    return h


def beta_incompleta_regularizada(a, b, x):

    if x <= 0.0:
        return 0.0

    if x >= 1.0:
        return 1.0

    bt = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )

    if x < (
        (a + 1.0)
        / (a + b + 2.0)
    ):

        return (
            bt
            * _betacf(a, b, x)
            / a
        )

    return (
        1.0
        - bt
        * _betacf(
            b,
            a,
            1.0 - x
        )
        / b
    )


def cdf_t_student(t, gl):
    """
    CDF da distribuição t de Student.
    """

    if gl <= 0:
        raise ValueError(
            "Graus de liberdade inválidos."
        )

    if t == 0:
        return 0.5

    x = (
        gl
        / (
            gl + t * t
        )
    )

    ib = beta_incompleta_regularizada(
        gl / 2.0,
        0.5,
        x
    )

    if t > 0:
        return (
            1.0
            - 0.5 * ib
        )

    return (
        0.5 * ib
    )


# ============================================================
# Teste t pareado
# ============================================================

def teste_t_pareado(diferencas):

    n = len(diferencas)

    if n < 2:
        return None, None

    media = statistics.mean(
        diferencas
    )

    desvio = statistics.stdev(
        diferencas
    )

    if desvio == 0:

        if media == 0:
            return 0.0, 1.0

        return math.inf, 0.0

    erro_padrao = (
        desvio
        / math.sqrt(n)
    )

    t = (
        media
        / erro_padrao
    )

    gl = n - 1

    p = (
        2.0
        * (
            1.0
            - cdf_t_student(
                abs(t),
                gl
            )
        )
    )

    p = max(
        0.0,
        min(1.0, p)
    )

    return t, p


# ============================================================
# Bootstrap pareado
# ============================================================

def bootstrap_pareado(
    pares,
    rng,
    num_bootstrap
):
    """
    Reamostra pares completos.

    Preserva a associação entre as duas implementações.
    """

    n = len(pares)

    medias_diferenca = []
    speedups_globais = []

    for _ in range(
        num_bootstrap
    ):

        reamostra = rng.choices(
            pares,
            k=n
        )

        ref = [
            p["tempo_referencia_ms"]
            for p in reamostra
        ]

        cmp_ = [
            p["tempo_comparada_ms"]
            for p in reamostra
        ]

        diferencas = [
            r - c
            for r, c
            in zip(ref, cmp_)
        ]

        medias_diferenca.append(
            statistics.mean(
                diferencas
            )
        )

        media_ref = statistics.mean(
            ref
        )

        media_cmp = statistics.mean(
            cmp_
        )

        if media_cmp != 0:
            speedups_globais.append(
                media_ref
                / media_cmp
            )

    medias_diferenca.sort()
    speedups_globais.sort()

    def intervalo_percentil(valores):

        nval = len(valores)

        inferior = int(
            0.025 * nval
        )

        superior = int(
            0.975 * nval
        ) - 1

        inferior = max(
            0,
            inferior
        )

        superior = min(
            nval - 1,
            superior
        )

        return (
            valores[inferior],
            valores[superior]
        )

    diff_inf, diff_sup = \
        intervalo_percentil(
            medias_diferenca
        )

    speed_inf, speed_sup = \
        intervalo_percentil(
            speedups_globais
        )

    return (
        diff_inf,
        diff_sup,
        speed_inf,
        speed_sup
    )


# ============================================================
# Teste de permutação pareado
# ============================================================

def teste_permutacao_pareado(
    diferencas,
    rng,
    num_permutacoes
):
    """
    Sob H0, troca-se aleatoriamente o sinal de cada diferença.

    Estatística:
        valor absoluto da média das diferenças.
    """

    observado = abs(
        statistics.mean(
            diferencas
        )
    )

    extremos = 0

    for _ in range(
        num_permutacoes
    ):

        permutadas = [
            d
            if rng.random() < 0.5
            else -d
            for d in diferencas
        ]

        estatistica = abs(
            statistics.mean(
                permutadas
            )
        )

        if estatistica >= observado:
            extremos += 1

    # Correção +1 evita p = 0.
    p = (
        extremos + 1
    ) / (
        num_permutacoes + 1
    )

    return observado, p


# ============================================================
# Estatísticas comparativas
# ============================================================

def analisar_pares(
    pares_por_tamanho,
    num_bootstrap,
    num_permutacoes,
    seed
):
    resultados = []

    rng_boot = random.Random(
        seed
    )

    rng_perm = random.Random(
        seed + 1
    )

    for tamanho in sorted(
        pares_por_tamanho
    ):

        pares = (
            pares_por_tamanho[
                tamanho
            ]
        )

        if len(pares) < 2:
            continue

        referencia = [
            p["tempo_referencia_ms"]
            for p in pares
        ]

        comparada = [
            p["tempo_comparada_ms"]
            for p in pares
        ]

        diferencas = [
            p["diferenca_ms"]
            for p in pares
        ]

        speedups_pareados = [
            p["speedup"]
            for p in pares
        ]

        n = len(pares)

        media_ref = statistics.mean(
            referencia
        )

        media_cmp = statistics.mean(
            comparada
        )

        media_diff = statistics.mean(
            diferencas
        )

        mediana_diff = statistics.median(
            diferencas
        )

        dp_diff = statistics.stdev(
            diferencas
        )

        speedup_global = (
            media_ref / media_cmp
            if media_cmp != 0
            else math.inf
        )

        speedup_mediano = (
            statistics.median(
                speedups_pareados
            )
        )

        speedup_medio_pareado = (
            statistics.mean(
                speedups_pareados
            )
        )

        # Tamanho de efeito para medidas pareadas.
        cohen_dz = (
            media_diff / dp_diff
            if dp_diff != 0
            else math.inf
        )

        (
            diff_boot_inf,
            diff_boot_sup,
            speed_boot_inf,
            speed_boot_sup
        ) = bootstrap_pareado(
            pares,
            rng_boot,
            num_bootstrap
        )

        t_stat, p_t = teste_t_pareado(
            diferencas
        )

        (
            estatistica_perm,
            p_perm
        ) = teste_permutacao_pareado(
            diferencas,
            rng_perm,
            num_permutacoes
        )

        resultados.append({

            "tamanho":
                tamanho,

            "n_pares":
                n,

            "media_referencia_ms":
                media_ref,

            "media_comparada_ms":
                media_cmp,

            "diferenca_media_ms":
                media_diff,

            "diferenca_mediana_ms":
                mediana_diff,

            "dp_diferenca_ms":
                dp_diff,

            "ic95_diff_boot_inf":
                diff_boot_inf,

            "ic95_diff_boot_sup":
                diff_boot_sup,

            "speedup_global":
                speedup_global,

            "speedup_medio_pareado":
                speedup_medio_pareado,

            "speedup_mediano":
                speedup_mediano,

            "ic95_speedup_boot_inf":
                speed_boot_inf,

            "ic95_speedup_boot_sup":
                speed_boot_sup,

            "cohen_dz":
                cohen_dz,

            "t_pareado":
                t_stat,

            "p_t_pareado":
                p_t,

            "estatistica_permutacao":
                estatistica_perm,

            "p_permutacao":
                p_perm
        })

    return resultados


# ============================================================
# CSV dos pares
# ============================================================

def salvar_pares(
    pares_por_tamanho,
    arquivo_saida
):
    with open(
        arquivo_saida,
        "w",
        newline="",
        encoding="utf-8"
    ) as arquivo:

        escritor = csv.writer(
            arquivo,
            lineterminator="\n"
        )

        escritor.writerow([
            "tamanho",
            "rodada",
            "tempo_referencia_ms",
            "tempo_comparada_ms",
            "diferenca_ms",
            "speedup"
        ])

        for tamanho in sorted(
            pares_por_tamanho
        ):

            for par in pares_por_tamanho[
                tamanho
            ]:

                escritor.writerow([
                    tamanho,
                    par["rodada"],

                    f"{par['tempo_referencia_ms']:.6f}",
                    f"{par['tempo_comparada_ms']:.6f}",
                    f"{par['diferenca_ms']:.6f}",
                    f"{par['speedup']:.6f}"
                ])


# ============================================================
# CSV da comparação
# ============================================================

def salvar_comparacao(
    resultados,
    arquivo_saida
):
    with open(
        arquivo_saida,
        "w",
        newline="",
        encoding="utf-8"
    ) as arquivo:

        escritor = csv.writer(
            arquivo,
            lineterminator="\n"
        )

        escritor.writerow([
            "tamanho",
            "n_pares",

            "media_referencia_ms",
            "media_comparada_ms",

            "diferenca_media_ms",
            "diferenca_mediana_ms",
            "dp_diferenca_ms",

            "ic95_diff_boot_inferior",
            "ic95_diff_boot_superior",

            "speedup_global",
            "speedup_medio_pareado",
            "speedup_mediano",

            "ic95_speedup_boot_inferior",
            "ic95_speedup_boot_superior",

            "cohen_dz",

            "t_pareado",
            "p_t_pareado",

            "p_permutacao"
        ])

        for r in resultados:

            escritor.writerow([
                r["tamanho"],
                r["n_pares"],

                f"{r['media_referencia_ms']:.6f}",
                f"{r['media_comparada_ms']:.6f}",

                f"{r['diferenca_media_ms']:.6f}",
                f"{r['diferenca_mediana_ms']:.6f}",
                f"{r['dp_diferenca_ms']:.6f}",

                f"{r['ic95_diff_boot_inf']:.6f}",
                f"{r['ic95_diff_boot_sup']:.6f}",

                f"{r['speedup_global']:.6f}",
                f"{r['speedup_medio_pareado']:.6f}",
                f"{r['speedup_mediano']:.6f}",

                f"{r['ic95_speedup_boot_inf']:.6f}",
                f"{r['ic95_speedup_boot_sup']:.6f}",

                f"{r['cohen_dz']:.6f}",

                f"{r['t_pareado']:.6f}",
                f"{r['p_t_pareado']:.6f}",

                f"{r['p_permutacao']:.6f}"
            ])


# ============================================================
# Saída textual
# ============================================================

def imprimir_resultados(
    resultados
):
    print()

    cabecalho = (
        f"{'tamanho':>10} "
        f"{'n':>4} "
        f"{'ref(ms)':>10} "
        f"{'comp(ms)':>10} "
        f"{'dif(ms)':>10} "
        f"{'speedup':>9} "
        f"{'ICsp_inf':>9} "
        f"{'ICsp_sup':>9} "
        f"{'dz':>8} "
        f"{'p_t':>9} "
        f"{'p_perm':>9}"
    )

    print(cabecalho)
    print("-" * len(cabecalho))

    for r in resultados:

        print(
            f"{r['tamanho']:>10} "
            f"{r['n_pares']:>4} "
            f"{r['media_referencia_ms']:>10.6f} "
            f"{r['media_comparada_ms']:>10.6f} "
            f"{r['diferenca_media_ms']:>10.6f} "
            f"{r['speedup_global']:>9.3f} "
            f"{r['ic95_speedup_boot_inf']:>9.3f} "
            f"{r['ic95_speedup_boot_sup']:>9.3f} "
            f"{r['cohen_dz']:>8.3f} "
            f"{r['p_t_pareado']:>9.5f} "
            f"{r['p_permutacao']:>9.5f}"
        )


# ============================================================
# Gráfico dos tempos médios
# ============================================================

def grafico_tempos_medios(
    resultados,
    referencia,
    comparada,
    arquivo_saida
):
    tamanhos = [
        r["tamanho"]
        for r in resultados
    ]

    ref = [
        r["media_referencia_ms"]
        for r in resultados
    ]

    cmp_ = [
        r["media_comparada_ms"]
        for r in resultados
    ]

    plt.figure(
        figsize=(9, 6)
    )

    plt.plot(
        tamanhos,
        ref,
        marker="o",
        label=referencia
    )

    plt.plot(
        tamanhos,
        cmp_,
        marker="o",
        label=comparada
    )

    plt.xscale("log")
    plt.yscale("log")

    plt.xlabel(
        "Tamanho do problema"
    )

    plt.ylabel(
        "Tempo médio (ms)"
    )

    plt.title(
        "Tempos médios das implementações"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        arquivo_saida,
        format="jpg",
        dpi=300
    )

    plt.close()


# ============================================================
# Gráfico de speedup
# ============================================================

def grafico_speedup(
    resultados,
    arquivo_saida
):
    tamanhos = [
        r["tamanho"]
        for r in resultados
    ]

    speedups = [
        r["speedup_global"]
        for r in resultados
    ]

    inferior = [
        r["ic95_speedup_boot_inf"]
        for r in resultados
    ]

    superior = [
        r["ic95_speedup_boot_sup"]
        for r in resultados
    ]

    erros_inf = [
        s - i
        for s, i
        in zip(speedups, inferior)
    ]

    erros_sup = [
        u - s
        for s, u
        in zip(speedups, superior)
    ]

    plt.figure(
        figsize=(9, 6)
    )

    plt.errorbar(
        tamanhos,
        speedups,
        yerr=[
            erros_inf,
            erros_sup
        ],
        marker="o",
        capsize=4
    )

    plt.axhline(
        y=1.0,
        linestyle="--"
    )

    plt.xscale("log")

    plt.xlabel(
        "Tamanho do problema"
    )

    plt.ylabel(
        "Speedup referência / comparada"
    )

    plt.title(
        "Speedup com IC95% bootstrap"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        arquivo_saida,
        format="jpg",
        dpi=300
    )

    plt.close()


# ============================================================
# Boxplot das diferenças
# ============================================================

def grafico_diferencas(
    pares_por_tamanho,
    arquivo_saida
):
    tamanhos = sorted(
        pares_por_tamanho
    )

    valores = []

    rotulos = []

    for tamanho in tamanhos:

        pares = pares_por_tamanho[
            tamanho
        ]

        if not pares:
            continue

        valores.append([
            p["diferenca_ms"]
            for p in pares
        ])

        rotulos.append(
            str(tamanho)
        )

    plt.figure(
        figsize=(9, 6)
    )

    plt.boxplot(
        valores,
        tick_labels=rotulos,
        showmeans=True
    )

    plt.axhline(
        y=0.0,
        linestyle="--"
    )

    plt.xlabel(
        "Tamanho do problema"
    )

    plt.ylabel(
        "Referência - comparada (ms)"
    )

    plt.title(
        "Distribuição das diferenças pareadas"
    )

    plt.grid(
        True,
        axis="y",
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        arquivo_saida,
        format="jpg",
        dpi=300
    )

    plt.close()


# ============================================================
# Relatório LaTeX
# ============================================================

def gerar_relatorio(
    diretorio,
    data_analise,
    linha_comando,
    referencia,
    comparada,
    resultados,
    num_bootstrap,
    num_permutacoes
):
    arquivo_saida = (
        diretorio
        / "relatorio_comparacao.tex"
    )

    with open(
        arquivo_saida,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
r"""\documentclass[11pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazil]{babel}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{float}
\usepackage{hyperref}

\geometry{margin=2.5cm}

\title{Relatório de Comparação de Desempenho}
\author{}
\date{}

\begin{document}

\maketitle

"""
        )

        f.write(
            "\\section{Identificação}\n\n"
        )

        f.write(
            "\\begin{tabular}{ll}\n"
        )

        f.write(
            "Data e hora: & "
            + escapar_latex(
                data_analise.strftime(
                    "%d/%m/%Y %H:%M:%S"
                )
            )
            + r" \\"
            + "\n"
        )

        f.write(
            "Implementação de referência: & "
            + r"\texttt{"
            + escapar_latex(referencia)
            + "}"
            + r" \\"
            + "\n"
        )

        f.write(
            "Implementação comparada: & "
            + r"\texttt{"
            + escapar_latex(comparada)
            + "}"
            + r" \\"
            + "\n"
        )

        f.write(
            "Bootstrap: & "
            + str(num_bootstrap)
            + " reamostragens"
            + r" \\"
            + "\n"
        )

        f.write(
            "Permutações: & "
            + str(num_permutacoes)
            + r" \\"
            + "\n"
        )

        f.write(
            "\\end{tabular}\n\n"
        )

        f.write(
            "\\subsection*{Linha de comando}\n"
            "\\begin{verbatim}\n"
            + linha_comando
            + "\n"
            "\\end{verbatim}\n\n"
        )

        f.write(
r"""\section{Metodologia}

As implementações foram comparadas utilizando observações
pareadas por rodada e tamanho do problema. Para cada rodada
foi calculada a diferença

\[
D_i =
T_{\mathrm{referencia},i}
-
T_{\mathrm{comparada},i}
\]

e o speedup

\[
S_i =
\frac{T_{\mathrm{referencia},i}}
     {T_{\mathrm{comparada},i}}.
\]

Valores positivos de $D_i$ indicam menor tempo para a
implementação comparada. Valores de speedup maiores que 1
também indicam vantagem para a implementação comparada.

O intervalo de confiança do speedup e da diferença média foi
estimado por bootstrap pareado, preservando juntas as duas
observações de cada rodada.

Também foram realizados um teste $t$ pareado e um teste de
permutação pareado por inversão aleatória dos sinais das
diferenças.

O tamanho de efeito foi expresso por $d_z$, calculado pela
razão entre a média e o desvio padrão das diferenças pareadas.

"""
        )

        f.write(
r"""\section{Tempos médios}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{tempos_medios.jpg}
    \caption{Tempos médios das implementações.}
\end{figure}

"""
        )

        f.write(
r"""\section{Speedup}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{speedup.jpg}
    \caption{Speedup da implementação comparada em relação à referência.}
\end{figure}

"""
        )

        f.write(
r"""\section{Diferenças pareadas}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{diferencas.jpg}
    \caption{Distribuição das diferenças pareadas entre os tempos.}
\end{figure}

"""
        )

        f.write(
r"""\section{Resultados}

\begin{longtable}{
    r
    r
    r
    r
    r
    r
    r
    r
}
\toprule
Tamanho &
Pares &
Ref. &
Comp. &
Dif. &
Speedup &
$p_t$ &
$p_{perm}$ \\
\midrule
\endhead
"""
        )

        for r in resultados:

            f.write(
                f"{r['tamanho']} & "
                f"{r['n_pares']} & "
                f"{r['media_referencia_ms']:.6f} & "
                f"{r['media_comparada_ms']:.6f} & "
                f"{r['diferenca_media_ms']:.6f} & "
                f"{r['speedup_global']:.3f} & "
                f"{r['p_t_pareado']:.5f} & "
                f"{r['p_permutacao']:.5f}"
                + r" \\"
                + "\n"
            )

        f.write(
r"""\bottomrule
\end{longtable}

"""
        )

        f.write(
r"""\subsection{Intervalos de confiança e tamanho de efeito}

\begin{longtable}{
    r
    r
    r
    r
    r
    r
}
\toprule
Tamanho &
Dif. inf. &
Dif. sup. &
Speedup inf. &
Speedup sup. &
$d_z$ \\
\midrule
\endhead
"""
        )

        for r in resultados:

            f.write(
                f"{r['tamanho']} & "
                f"{r['ic95_diff_boot_inf']:.6f} & "
                f"{r['ic95_diff_boot_sup']:.6f} & "
                f"{r['ic95_speedup_boot_inf']:.3f} & "
                f"{r['ic95_speedup_boot_sup']:.3f} & "
                f"{r['cohen_dz']:.3f}"
                + r" \\"
                + "\n"
            )

        f.write(
r"""\bottomrule
\end{longtable}

"""
        )

        f.write(
            "\\section{Síntese por tamanho}\n\n"
        )

        for r in resultados:

            f.write(
                "\\subsection{Tamanho "
                + str(r["tamanho"])
                + "}\n\n"
            )

            f.write(
                "Foram utilizados "
                f"{r['n_pares']} pares. "
                "O tempo médio da referência foi "
                f"{r['media_referencia_ms']:.6f} ms "
                "e o da implementação comparada foi "
                f"{r['media_comparada_ms']:.6f} ms. "
            )

            f.write(
                "A diferença média referência--comparada "
                "foi de "
                f"{r['diferenca_media_ms']:.6f} ms. "
            )

            f.write(
                "O speedup baseado na razão entre as médias "
                "foi de "
                f"{r['speedup_global']:.3f}, "
                "com IC95\\% bootstrap "
                f"[{r['ic95_speedup_boot_inf']:.3f}; "
                f"{r['ic95_speedup_boot_sup']:.3f}]. "
            )

            f.write(
                "O teste $t$ pareado apresentou "
                f"$p={r['p_t_pareado']:.5f}$ "
                "e o teste de permutação pareado "
                f"$p={r['p_permutacao']:.5f}$. "
            )

            f.write(
                "O tamanho de efeito $d_z$ foi "
                f"{r['cohen_dz']:.3f}."
                "\n\n"
            )

        f.write(
r"""\section{Arquivos associados}

\begin{itemize}
    \item \texttt{coleta.csv}: dados brutos;
    \item \texttt{pares.csv}: observações pareadas;
    \item \texttt{comparacao.csv}: resultados estatísticos;
    \item \texttt{comparacao.py}: versão do programa utilizada;
    \item \texttt{tempos\_medios.jpg}: tempos médios;
    \item \texttt{speedup.jpg}: speedup por tamanho;
    \item \texttt{diferencas.jpg}: distribuição das diferenças.
\end{itemize}

\end{document}
"""
        )

    return arquivo_saida


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Compara duas implementações utilizando "
            "observações pareadas por rodada."
        )
    )

    parser.add_argument(
        "arquivo",
        help="Arquivo coleta.csv"
    )

    parser.add_argument(
        "--referencia",
        required=True,
        help=(
            "Executável utilizado como referência "
            "no cálculo do speedup"
        )
    )

    parser.add_argument(
        "--comparada",
        required=True,
        help="Executável que será comparado à referência"
    )

    parser.add_argument(
        "--tamanhos",
        nargs="+",
        type=int,
        required=True,
        help="Tamanhos de problema considerados"
    )

    parser.add_argument(
        "--bootstrap",
        type=int,
        default=NUM_BOOTSTRAP_PADRAO,
        help=(
            "Número de reamostragens bootstrap "
            f"(padrão: {NUM_BOOTSTRAP_PADRAO})"
        )
    )

    parser.add_argument(
        "--permutacoes",
        type=int,
        default=NUM_PERMUTACOES_PADRAO,
        help=(
            "Número de permutações "
            f"(padrão: {NUM_PERMUTACOES_PADRAO})"
        )
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=SEED_PADRAO,
        help=(
            "Semente aleatória "
            f"(padrão: {SEED_PADRAO})"
        )
    )

    args = parser.parse_args()

    arquivo_coleta = Path(
        args.arquivo
    )

    try:

        anunciar(
            "1. Criação do registro da comparação"
        )

        diretorio, data_analise = \
            criar_diretorio_registro(
                arquivo_coleta
            )

        print(
            f"Diretório: {diretorio}"
        )

        anunciar(
            "2. Leitura dos dados"
        )

        dados = ler_dados(
            arquivo_coleta
        )

        print(
            f"{len(dados)} observações lidas."
        )

        anunciar(
            "3. Formação dos pares por rodada"
        )

        pares, avisos = formar_pares(
            dados,
            args.referencia,
            args.comparada,
            set(args.tamanhos)
        )

        for aviso in avisos:
            print(
                "AVISO:",
                aviso,
                file=sys.stderr
            )

        total_pares = sum(
            len(p)
            for p in pares.values()
        )

        print(
            f"{total_pares} pares válidos encontrados."
        )

        for tamanho in sorted(pares):
            print(
                f"tamanho={tamanho}: "
                f"{len(pares[tamanho])} pares"
            )

        anunciar(
            "4. Análise estatística pareada"
        )

        resultados = analisar_pares(
            pares,
            args.bootstrap,
            args.permutacoes,
            args.seed
        )

        imprimir_resultados(
            resultados
        )

        anunciar(
            "5. Gravação dos dados pareados"
        )

        salvar_pares(
            pares,
            diretorio / "pares.csv"
        )

        print(
            f"Gerado: {diretorio / 'pares.csv'}"
        )

        anunciar(
            "6. Gravação da tabela de comparação"
        )

        salvar_comparacao(
            resultados,
            diretorio / "comparacao.csv"
        )

        print(
            f"Gerado: {diretorio / 'comparacao.csv'}"
        )

        anunciar(
            "7. Gráfico dos tempos médios"
        )

        grafico_tempos_medios(
            resultados,
            args.referencia,
            args.comparada,
            diretorio / "tempos_medios.jpg"
        )

        print(
            f"Gerado: "
            f"{diretorio / 'tempos_medios.jpg'}"
        )

        anunciar(
            "8. Gráfico de speedup"
        )

        grafico_speedup(
            resultados,
            diretorio / "speedup.jpg"
        )

        print(
            f"Gerado: "
            f"{diretorio / 'speedup.jpg'}"
        )

        anunciar(
            "9. Boxplot das diferenças pareadas"
        )

        grafico_diferencas(
            pares,
            diretorio / "diferencas.jpg"
        )

        print(
            f"Gerado: "
            f"{diretorio / 'diferencas.jpg'}"
        )

        anunciar(
            "10. Geração do relatório LaTeX"
        )

        linha_comando = (
            " ".join(sys.argv)
        )

        arquivo_relatorio = gerar_relatorio(
            diretorio,
            data_analise,
            linha_comando,
            args.referencia,
            args.comparada,
            resultados,
            args.bootstrap,
            args.permutacoes
        )

        print(
            f"Gerado: {arquivo_relatorio}"
        )

        anunciar(
            "Comparação concluída"
        )

        print(
            f"Resultados armazenados em:\n"
            f"    {diretorio}"
        )

    except Exception as erro:

        print(
            f"Erro: {erro}",
            file=sys.stderr
        )

        sys.exit(1)


if __name__ == "__main__":
    main()
