#!/usr/bin/env python3

import sys
import csv
import math
import random
import shutil
import statistics

from datetime import datetime
from pathlib import Path
from statistics import NormalDist

import matplotlib.pyplot as plt


# ============================================================
# Configuração geral
# ============================================================

NUM_BOOTSTRAP = 10000
BOOTSTRAP_SEED = 12345

PERCENTUAL_APARADO = 0.10
MAX_LAG_AUTOCORRELACAO = 5


# ============================================================
# Utilidades
# ============================================================

def anunciar(texto):
    print()
    print("=" * 72)
    print(texto)
    print("=" * 72)


def nome_seguro(texto):
    """
    Converte um texto em um nome adequado para arquivo.
    """

    return "".join(
        c if c.isalnum() or c in "-_" else "_"
        for c in texto
    )


def escapar_latex(texto):
    """
    Escapa caracteres especiais utilizados pelo LaTeX.
    """

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
# Criação do registro da análise
# ============================================================

def criar_diretorio_registro(arquivo_coleta):
    """
    Cria um diretório:

        Registro-AAAAMMDD-HHMMSS

    e copia para ele:
      - o arquivo coleta.csv usado;
      - o próprio analise.py.

    Isso permite preservar os dados e o código que produziram
    uma determinada análise.
    """

    agora = datetime.now()

    nome = agora.strftime(
        "Registro-%Y%m%d-%H%M%S"
    )

    diretorio = Path(nome)

    # Evita colisão extremamente improvável caso duas análises
    # sejam iniciadas no mesmo segundo.
    contador = 1

    while diretorio.exists():
        diretorio = Path(
            f"{nome}-{contador}"
        )
        contador += 1

    diretorio.mkdir()

    shutil.copy2(
        arquivo_coleta,
        diretorio / "coleta.csv"
    )

    try:
        caminho_script = Path(__file__).resolve()

        shutil.copy2(
            caminho_script,
            diretorio / "analise.py"
        )

    except Exception:
        # A análise pode continuar mesmo que não seja possível
        # copiar o próprio script.
        pass

    return diretorio, agora


# ============================================================
# Leitura dos dados
# ============================================================

def ler_dados(arquivo_csv):
    """
    Formato esperado:

        rodada,ordem,executavel,nome,tamanho,tempo_ms
    """

    dados = []

    with open(
        arquivo_csv,
        "r",
        encoding="utf-8"
    ) as arquivo:

        leitor = csv.DictReader(
            arquivo
        )

        campos_necessarios = {
            "rodada",
            "ordem",
            "executavel",
            "nome",
            "tamanho",
            "tempo_ms"
        }

        if leitor.fieldnames is None:
            raise ValueError(
                "O CSV não possui cabeçalho."
            )

        faltantes = (
            campos_necessarios
            - set(leitor.fieldnames)
        )

        if faltantes:
            raise ValueError(
                "Campos ausentes no CSV: "
                + ", ".join(sorted(faltantes))
            )

        for linha in leitor:

            dados.append({
                "rodada":
                    int(linha["rodada"]),

                "ordem":
                    int(linha["ordem"]),

                "executavel":
                    linha["executavel"],

                "nome":
                    linha["nome"],

                "tamanho":
                    int(linha["tamanho"]),

                "tempo_ms":
                    float(linha["tempo_ms"])
            })

    return dados


def filtrar_tamanhos(
    dados,
    tamanhos
):
    return [
        registro
        for registro in dados
        if registro["tamanho"]
        in tamanhos
    ]


def obter_casos(dados):
    """
    Agrupa as observações por:

        executável x tamanho
    """

    casos = {}

    for registro in dados:

        chave = (
            registro["executavel"],
            registro["tamanho"]
        )

        casos.setdefault(
            chave,
            []
        ).append(registro)

    # Preserva ordem temporal das observações de cada caso.
    for registros in casos.values():

        registros.sort(
            key=lambda x: x["ordem"]
        )

    return casos


# ============================================================
# Gráfico de dispersão
# ============================================================

def gerar_grafico_dispersao(
    dados,
    arquivo_saida
):
    """
    Eixo X: ordem global de execução
    Eixo Y: tempo em milissegundos
    """

    executaveis = sorted(
        set(
            r["executavel"]
            for r in dados
        )
    )

    tamanhos = sorted(
        set(
            r["tamanho"]
            for r in dados
        )
    )

    plt.figure(
        figsize=(12, 7)
    )

    for executavel in executaveis:

        for tamanho in tamanhos:

            pontos = [
                r
                for r in dados
                if (
                    r["executavel"]
                    == executavel
                    and
                    r["tamanho"]
                    == tamanho
                )
            ]

            if not pontos:
                continue

            ordens = [
                r["ordem"]
                for r in pontos
            ]

            tempos = [
                r["tempo_ms"]
                for r in pontos
            ]

            plt.scatter(
                ordens,
                tempos,
                label=(
                    f"{executavel} "
                    f"- n={tamanho}"
                ),
                alpha=0.75
            )

    plt.xlabel(
        "Ordem de execução"
    )

    plt.ylabel(
        "Tempo (ms)"
    )

    plt.title(
        "Dispersão dos tempos de execução"
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
# Boxplot
# ============================================================

def gerar_boxplot(
    casos,
    arquivo_saida
):
    valores = []
    rotulos = []

    for (
        executavel,
        tamanho
    ), registros in sorted(
        casos.items(),
        key=lambda x: (
            x[0][1],
            x[0][0]
        )
    ):

        valores.append(
            [
                r["tempo_ms"]
                for r in registros
            ]
        )

        rotulos.append(
            f"{executavel}\n"
            f"n={tamanho}"
        )

    plt.figure(
        figsize=(12, 7)
    )

    plt.boxplot(
        valores,
        tick_labels=rotulos,
        showmeans=True
    )

    plt.xlabel(
        "Caso experimental"
    )

    plt.ylabel(
        "Tempo (ms)"
    )

    plt.title(
        "Distribuição dos tempos de execução"
    )

    plt.grid(
        True,
        axis="y",
        alpha=0.3
    )

    plt.xticks(
        rotation=45,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        arquivo_saida,
        format="jpg",
        dpi=300
    )

    plt.close()


# ============================================================
# Histogramas
# ============================================================

def gerar_histogramas(
    casos,
    diretorio
):
    diretorio.mkdir(
        exist_ok=True
    )

    arquivos = {}

    for (
        executavel,
        tamanho
    ), registros in casos.items():

        tempos = [
            r["tempo_ms"]
            for r in registros
        ]

        plt.figure(
            figsize=(8, 6)
        )

        plt.hist(
            tempos,
            bins="auto"
        )

        plt.xlabel(
            "Tempo (ms)"
        )

        plt.ylabel(
            "Frequência"
        )

        plt.title(
            f"Histograma - "
            f"{executavel} - "
            f"n={tamanho}"
        )

        plt.grid(
            True,
            axis="y",
            alpha=0.3
        )

        plt.tight_layout()

        nome = (
            f"{nome_seguro(executavel)}_"
            f"{tamanho}.jpg"
        )

        caminho = diretorio / nome

        plt.savefig(
            caminho,
            format="jpg",
            dpi=300
        )

        plt.close()

        arquivos[
            (executavel, tamanho)
        ] = caminho

    return arquivos


# ============================================================
# Q-Q plots
# ============================================================

def gerar_qqplots(
    casos,
    diretorio
):
    diretorio.mkdir(
        exist_ok=True
    )

    normal = NormalDist()

    arquivos = {}

    for (
        executavel,
        tamanho
    ), registros in casos.items():

        tempos = sorted(
            r["tempo_ms"]
            for r in registros
        )

        n = len(tempos)

        if n < 2:
            continue

        media = statistics.mean(
            tempos
        )

        desvio = statistics.stdev(
            tempos
        )

        teoricos = []

        for i in range(
            1,
            n + 1
        ):

            p = (
                i - 0.5
            ) / n

            z = normal.inv_cdf(p)

            teoricos.append(
                media
                + z * desvio
            )

        minimo = min(
            min(teoricos),
            min(tempos)
        )

        maximo = max(
            max(teoricos),
            max(tempos)
        )

        plt.figure(
            figsize=(7, 7)
        )

        plt.scatter(
            teoricos,
            tempos
        )

        plt.plot(
            [minimo, maximo],
            [minimo, maximo]
        )

        plt.xlabel(
            "Quantis teóricos normais"
        )

        plt.ylabel(
            "Quantis observados"
        )

        plt.title(
            f"Q-Q plot - "
            f"{executavel} - "
            f"n={tamanho}"
        )

        plt.grid(
            True,
            alpha=0.3
        )

        plt.tight_layout()

        nome = (
            f"{nome_seguro(executavel)}_"
            f"{tamanho}.jpg"
        )

        caminho = diretorio / nome

        plt.savefig(
            caminho,
            format="jpg",
            dpi=300
        )

        plt.close()

        arquivos[
            (executavel, tamanho)
        ] = caminho

    return arquivos


# ============================================================
# Valores críticos t de Student
# IC bilateral de 95%
# ============================================================

T_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042
}


def valor_t_95(n):
    gl = n - 1

    if gl <= 0:
        raise ValueError(
            "São necessárias pelo menos duas amostras."
        )

    if gl <= 30:
        return T_95[gl]

    # Aproximação normal para amostras maiores.
    return 1.96


# ============================================================
# Quartis
# ============================================================

def calcular_quartis(
    amostras
):
    quartis = statistics.quantiles(
        amostras,
        n=4,
        method="inclusive"
    )

    q1 = quartis[0]
    q3 = quartis[2]

    iqr = q3 - q1

    return (
        q1,
        q3,
        iqr
    )


# ============================================================
# Média aparada
# ============================================================

def media_aparada(
    amostras,
    percentual=PERCENTUAL_APARADO
):
    dados = sorted(
        amostras
    )

    n = len(dados)

    remover = int(
        n * percentual
    )

    if remover == 0:
        return statistics.mean(
            dados
        )

    if 2 * remover >= n:
        return statistics.mean(
            dados
        )

    dados = dados[
        remover:n-remover
    ]

    return statistics.mean(
        dados
    )


# ============================================================
# Assimetria
# ============================================================

def calcular_assimetria(
    amostras
):
    n = len(amostras)

    if n < 3:
        return 0.0

    media = statistics.mean(
        amostras
    )

    s = statistics.stdev(
        amostras
    )

    if s == 0:
        return 0.0

    soma = sum(
        (
            (x - media) / s
        ) ** 3
        for x in amostras
    )

    return (
        n
        / (
            (n - 1)
            * (n - 2)
        )
        * soma
    )


# ============================================================
# Curtose em excesso
# ============================================================

def calcular_curtose(
    amostras
):
    n = len(amostras)

    if n < 4:
        return 0.0

    media = statistics.mean(
        amostras
    )

    s = statistics.stdev(
        amostras
    )

    if s == 0:
        return 0.0

    soma = sum(
        (
            (x - media) / s
        ) ** 4
        for x in amostras
    )

    termo1 = (
        n * (n + 1)
        / (
            (n - 1)
            * (n - 2)
            * (n - 3)
        )
        * soma
    )

    termo2 = (
        3
        * (n - 1) ** 2
        / (
            (n - 2)
            * (n - 3)
        )
    )

    return (
        termo1 - termo2
    )


# ============================================================
# Outliers pelo critério 1,5 x IQR
# ============================================================

def identificar_outliers(
    amostras
):
    q1, q3, iqr = \
        calcular_quartis(
            amostras
        )

    limite_inferior = (
        q1
        - 1.5 * iqr
    )

    limite_superior = (
        q3
        + 1.5 * iqr
    )

    outliers = [
        x
        for x in amostras
        if (
            x < limite_inferior
            or
            x > limite_superior
        )
    ]

    return (
        outliers,
        limite_inferior,
        limite_superior
    )


# ============================================================
# Bootstrap para a média
# ============================================================

def calcular_ic_bootstrap(
    amostras,
    rng,
    num_reamostragens=NUM_BOOTSTRAP,
    nivel=0.95
):
    n = len(amostras)

    medias = []

    for _ in range(
        num_reamostragens
    ):

        reamostra = rng.choices(
            amostras,
            k=n
        )

        medias.append(
            statistics.mean(
                reamostra
            )
        )

    medias.sort()

    alpha = (
        1.0 - nivel
    )

    indice_inf = int(
        alpha
        / 2.0
        * num_reamostragens
    )

    indice_sup = int(
        (
            1.0
            - alpha / 2.0
        )
        * num_reamostragens
    ) - 1

    indice_inf = max(
        0,
        indice_inf
    )

    indice_sup = min(
        num_reamostragens - 1,
        indice_sup
    )

    ic_inf = medias[
        indice_inf
    ]

    ic_sup = medias[
        indice_sup
    ]

    media = statistics.mean(
        amostras
    )

    margem = (
        ic_sup - ic_inf
    ) / 2.0

    margem_relativa = (
        margem / media
        if media != 0
        else 0.0
    )

    return (
        ic_inf,
        ic_sup,
        margem_relativa
    )


# ============================================================
# Jarque-Bera
# ============================================================

def jarque_bera(
    amostras
):
    n = len(amostras)

    skew = calcular_assimetria(
        amostras
    )

    kurt = calcular_curtose(
        amostras
    )

    jb = (
        n / 6.0
    ) * (
        skew ** 2
        + (
            kurt ** 2
            / 4.0
        )
    )

    # Para qui-quadrado com 2 graus de liberdade,
    # P(X >= x) = exp(-x/2).
    p = math.exp(
        -jb / 2.0
    )

    return (
        jb,
        p
    )


# ============================================================
# Correlação de Pearson
# ============================================================

def correlacao_pearson(
    x,
    y
):
    if len(x) != len(y):
        raise ValueError(
            "Vetores de tamanhos diferentes."
        )

    media_x = statistics.mean(
        x
    )

    media_y = statistics.mean(
        y
    )

    numerador = sum(
        (
            a - media_x
        )
        * (
            b - media_y
        )
        for a, b
        in zip(x, y)
    )

    den_x = math.sqrt(
        sum(
            (
                a - media_x
            ) ** 2
            for a in x
        )
    )

    den_y = math.sqrt(
        sum(
            (
                b - media_y
            ) ** 2
            for b in y
        )
    )

    if (
        den_x == 0
        or
        den_y == 0
    ):
        return 0.0

    return (
        numerador
        / (
            den_x
            * den_y
        )
    )


# ============================================================
# Ranks para Spearman
# ============================================================

def ranks(
    valores
):
    ordenados = sorted(
        enumerate(valores),
        key=lambda x: x[1]
    )

    resultado = [
        0.0
    ] * len(valores)

    i = 0

    while i < len(
        ordenados
    ):

        j = i

        while (
            j + 1
            < len(ordenados)
            and
            ordenados[j + 1][1]
            == ordenados[i][1]
        ):
            j += 1

        rank_medio = (
            i + j + 2
        ) / 2.0

        for k in range(
            i,
            j + 1
        ):
            resultado[
                ordenados[k][0]
            ] = rank_medio

        i = j + 1

    return resultado


def correlacao_spearman(
    x,
    y
):
    return correlacao_pearson(
        ranks(x),
        ranks(y)
    )


# ============================================================
# Regressão linear para tendência temporal
# ============================================================

def regressao_linear(
    x,
    y
):
    media_x = statistics.mean(
        x
    )

    media_y = statistics.mean(
        y
    )

    denominador = sum(
        (
            xi - media_x
        ) ** 2
        for xi in x
    )

    if denominador == 0:
        return (
            0.0,
            media_y,
            0.0
        )

    slope = (
        sum(
            (
                xi - media_x
            )
            * (
                yi - media_y
            )
            for xi, yi
            in zip(x, y)
        )
        / denominador
    )

    intercepto = (
        media_y
        - slope * media_x
    )

    previstos = [
        intercepto
        + slope * xi
        for xi in x
    ]

    ss_res = sum(
        (
            yi - pi
        ) ** 2
        for yi, pi
        in zip(
            y,
            previstos
        )
    )

    ss_tot = sum(
        (
            yi - media_y
        ) ** 2
        for yi in y
    )

    if ss_tot == 0:
        r2 = 0.0
    else:
        r2 = (
            1.0
            - ss_res / ss_tot
        )

    return (
        slope,
        intercepto,
        r2
    )


# ============================================================
# Autocorrelação
# ============================================================

def autocorrelacao(
    amostras,
    lag
):
    n = len(amostras)

    if (
        lag <= 0
        or
        lag >= n
    ):
        return None

    media = statistics.mean(
        amostras
    )

    denominador = sum(
        (
            x - media
        ) ** 2
        for x in amostras
    )

    if denominador == 0:
        return 0.0

    numerador = sum(
        (
            amostras[i]
            - media
        )
        * (
            amostras[i + lag]
            - media
        )
        for i in range(
            n - lag
        )
    )

    return (
        numerador
        / denominador
    )


# ============================================================
# Convergência da média
# ============================================================

def gerar_convergencia(
    casos,
    diretorio
):
    diretorio.mkdir(
        exist_ok=True
    )

    arquivos = {}

    for (
        executavel,
        tamanho
    ), registros in casos.items():

        tempos = [
            r["tempo_ms"]
            for r in registros
        ]

        medias = []

        acumulado = 0.0

        for indice, valor in enumerate(
            tempos,
            start=1
        ):

            acumulado += valor

            medias.append(
                acumulado / indice
            )

        plt.figure(
            figsize=(8, 6)
        )

        plt.plot(
            range(
                1,
                len(medias) + 1
            ),
            medias,
            marker="o"
        )

        plt.xlabel(
            "Número de amostras"
        )

        plt.ylabel(
            "Média acumulada (ms)"
        )

        plt.title(
            "Convergência da média - "
            f"{executavel} - "
            f"n={tamanho}"
        )

        plt.grid(
            True,
            alpha=0.3
        )

        plt.tight_layout()

        nome = (
            f"{nome_seguro(executavel)}_"
            f"{tamanho}.jpg"
        )

        caminho = (
            diretorio
            / nome
        )

        plt.savefig(
            caminho,
            format="jpg",
            dpi=300
        )

        plt.close()

        arquivos[
            (executavel, tamanho)
        ] = caminho

    return arquivos


# ============================================================
# Cálculo de todas as estatísticas
# ============================================================

def calcular_estatisticas(
    casos
):
    resultados = []

    rng = random.Random(
        BOOTSTRAP_SEED
    )

    for (
        executavel,
        tamanho
    ), registros in sorted(
        casos.items(),
        key=lambda x: (
            x[0][1],
            x[0][0]
        )
    ):

        tempos = [
            r["tempo_ms"]
            for r in registros
        ]

        ordens = [
            r["ordem"]
            for r in registros
        ]

        n = len(
            tempos
        )

        if n < 2:
            continue

        # ----------------------------------------------------
        # Estatísticas descritivas
        # ----------------------------------------------------

        media = statistics.mean(
            tempos
        )

        mediana = statistics.median(
            tempos
        )

        aparada = media_aparada(
            tempos
        )

        minimo = min(
            tempos
        )

        maximo = max(
            tempos
        )

        q1, q3, iqr = \
            calcular_quartis(
                tempos
            )

        desvio = statistics.stdev(
            tempos
        )

        cv = (
            desvio / media
            if media != 0
            else 0.0
        )

        assimetria = \
            calcular_assimetria(
                tempos
            )

        curtose = \
            calcular_curtose(
                tempos
            )

        # ----------------------------------------------------
        # Outliers
        # ----------------------------------------------------

        (
            outliers,
            lim_out_inf,
            lim_out_sup
        ) = identificar_outliers(
            tempos
        )

        percentual_outliers = (
            len(outliers)
            / n
            * 100.0
        )

        # ----------------------------------------------------
        # IC95% por t de Student
        # ----------------------------------------------------

        t = valor_t_95(
            n
        )

        erro_padrao = (
            desvio
            / math.sqrt(n)
        )

        margem_t = (
            t
            * erro_padrao
        )

        ic_t_inf = (
            media
            - margem_t
        )

        ic_t_sup = (
            media
            + margem_t
        )

        margem_t_relativa = (
            margem_t / media
            if media != 0
            else 0.0
        )

        # ----------------------------------------------------
        # IC95% bootstrap
        # ----------------------------------------------------

        (
            ic_boot_inf,
            ic_boot_sup,
            margem_boot_relativa
        ) = calcular_ic_bootstrap(
            tempos,
            rng
        )

        # ----------------------------------------------------
        # Normalidade
        # ----------------------------------------------------

        jb, jb_p = jarque_bera(
            tempos
        )

        # ----------------------------------------------------
        # Tendência temporal
        # ----------------------------------------------------

        (
            slope,
            intercepto,
            r2
        ) = regressao_linear(
            ordens,
            tempos
        )

        pearson = (
            correlacao_pearson(
                ordens,
                tempos
            )
        )

        spearman = (
            correlacao_spearman(
                ordens,
                tempos
            )
        )

        resultados.append({

            "executavel":
                executavel,

            "tamanho":
                tamanho,

            "n":
                n,

            "media_ms":
                media,

            "mediana_ms":
                mediana,

            "media_aparada_ms":
                aparada,

            "desvio_ms":
                desvio,

            "cv":
                cv,

            "minimo_ms":
                minimo,

            "q1_ms":
                q1,

            "q3_ms":
                q3,

            "maximo_ms":
                maximo,

            "iqr_ms":
                iqr,

            "assimetria":
                assimetria,

            "curtose_excesso":
                curtose,

            "num_outliers":
                len(outliers),

            "percentual_outliers":
                percentual_outliers,

            "limite_outlier_inf":
                lim_out_inf,

            "limite_outlier_sup":
                lim_out_sup,

            "ic_t_inf":
                ic_t_inf,

            "ic_t_sup":
                ic_t_sup,

            "margem_t":
                margem_t_relativa,

            "ic_boot_inf":
                ic_boot_inf,

            "ic_boot_sup":
                ic_boot_sup,

            "margem_boot":
                margem_boot_relativa,

            "jarque_bera":
                jb,

            "jarque_bera_p":
                jb_p,

            "tendencia_slope":
                slope,

            "tendencia_intercepto":
                intercepto,

            "tendencia_r2":
                r2,

            "correlacao_pearson":
                pearson,

            "correlacao_spearman":
                spearman
        })

    return resultados


# ============================================================
# Impressão resumida
# ============================================================

def imprimir_estatisticas(
    resultados
):
    print()

    cabecalho = (
        f"{'executavel':<18} "
        f"{'tam':>9} "
        f"{'n':>3} "
        f"{'media':>9} "
        f"{'mediana':>9} "
        f"{'apar10%':>9} "
        f"{'DP':>9} "
        f"{'CV%':>7} "
        f"{'skew':>7} "
        f"{'kurt':>7} "
        f"{'out':>4} "
        f"{'Mt%':>7} "
        f"{'Mb%':>7}"
    )

    print(
        cabecalho
    )

    print(
        "-" * len(cabecalho)
    )

    for r in resultados:

        print(
            f"{r['executavel']:<18} "
            f"{r['tamanho']:>9} "
            f"{r['n']:>3} "
            f"{r['media_ms']:>9.6f} "
            f"{r['mediana_ms']:>9.6f} "
            f"{r['media_aparada_ms']:>9.6f} "
            f"{r['desvio_ms']:>9.6f} "
            f"{r['cv'] * 100:>7.2f} "
            f"{r['assimetria']:>7.2f} "
            f"{r['curtose_excesso']:>7.2f} "
            f"{r['num_outliers']:>4} "
            f"{r['margem_t'] * 100:>7.2f} "
            f"{r['margem_boot'] * 100:>7.2f}"
        )


# ============================================================
# Arquivo estatisticas.csv
# ============================================================

def salvar_estatisticas(
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
            "executavel",
            "tamanho",
            "n",

            "media_ms",
            "mediana_ms",
            "media_aparada_10_ms",

            "desvio_ms",
            "cv_percentual",

            "minimo_ms",
            "q1_ms",
            "q3_ms",
            "maximo_ms",
            "iqr_ms",

            "assimetria",
            "curtose_excesso",

            "num_outliers",
            "percentual_outliers",
            "limite_outlier_inferior",
            "limite_outlier_superior",

            "ic95_t_inferior_ms",
            "ic95_t_superior_ms",
            "margem_t_percentual",

            "ic95_boot_inferior_ms",
            "ic95_boot_superior_ms",
            "margem_boot_percentual",

            "jarque_bera",
            "jarque_bera_p",

            "tendencia_ms_por_ordem",
            "tendencia_r2",

            "correlacao_pearson_ordem",
            "correlacao_spearman_ordem"
        ])

        for r in resultados:

            escritor.writerow([

                r["executavel"],
                r["tamanho"],
                r["n"],

                f"{r['media_ms']:.6f}",
                f"{r['mediana_ms']:.6f}",
                f"{r['media_aparada_ms']:.6f}",

                f"{r['desvio_ms']:.6f}",
                f"{r['cv'] * 100:.2f}",

                f"{r['minimo_ms']:.6f}",
                f"{r['q1_ms']:.6f}",
                f"{r['q3_ms']:.6f}",
                f"{r['maximo_ms']:.6f}",
                f"{r['iqr_ms']:.6f}",

                f"{r['assimetria']:.6f}",
                f"{r['curtose_excesso']:.6f}",

                r["num_outliers"],
                f"{r['percentual_outliers']:.2f}",

                f"{r['limite_outlier_inf']:.6f}",
                f"{r['limite_outlier_sup']:.6f}",

                f"{r['ic_t_inf']:.6f}",
                f"{r['ic_t_sup']:.6f}",
                f"{r['margem_t'] * 100:.2f}",

                f"{r['ic_boot_inf']:.6f}",
                f"{r['ic_boot_sup']:.6f}",
                f"{r['margem_boot'] * 100:.2f}",

                f"{r['jarque_bera']:.6f}",
                f"{r['jarque_bera_p']:.6f}",

                f"{r['tendencia_slope']:.10f}",
                f"{r['tendencia_r2']:.6f}",

                f"{r['correlacao_pearson']:.6f}",
                f"{r['correlacao_spearman']:.6f}"
            ])


# ============================================================
# Arquivo outliers.csv
# ============================================================

def salvar_outliers(
    casos,
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
            "executavel",
            "tamanho",
            "rodada",
            "ordem",
            "tempo_ms"
        ])

        for (
            executavel,
            tamanho
        ), registros in sorted(
            casos.items()
        ):

            tempos = [
                r["tempo_ms"]
                for r in registros
            ]

            (
                _,
                limite_inf,
                limite_sup
            ) = identificar_outliers(
                tempos
            )

            for registro in registros:

                tempo = (
                    registro["tempo_ms"]
                )

                if (
                    tempo < limite_inf
                    or
                    tempo > limite_sup
                ):

                    escritor.writerow([
                        executavel,
                        tamanho,
                        registro["rodada"],
                        registro["ordem"],
                        f"{tempo:.6f}"
                    ])


# ============================================================
# Arquivo autocorrelacao.csv
# ============================================================

def salvar_autocorrelacao(
    casos,
    arquivo_saida
):
    resultados = []

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
            "executavel",
            "tamanho",
            "lag",
            "autocorrelacao"
        ])

        for (
            executavel,
            tamanho
        ), registros in sorted(
            casos.items()
        ):

            tempos = [
                r["tempo_ms"]
                for r in registros
            ]

            max_lag = min(
                MAX_LAG_AUTOCORRELACAO,
                len(tempos) - 1
            )

            for lag in range(
                1,
                max_lag + 1
            ):

                valor = autocorrelacao(
                    tempos,
                    lag
                )

                escritor.writerow([
                    executavel,
                    tamanho,
                    lag,
                    f"{valor:.6f}"
                ])

                resultados.append({
                    "executavel":
                        executavel,

                    "tamanho":
                        tamanho,

                    "lag":
                        lag,

                    "autocorrelacao":
                        valor
                })

    return resultados


# ============================================================
# Relatório LaTeX
# ============================================================

def gerar_relatorio_latex(
    diretorio,
    data_analise,
    linha_comando,
    resultados,
    autocorrelacoes,
    arquivos_histogramas,
    arquivos_qq,
    arquivos_convergencia
):
    """
    Gera um relatório LaTeX completo com as informações da
    análise atual.
    """

    arquivo_saida = (
        diretorio
        / "relatorio.tex"
    )

    executaveis = sorted(
        set(
            r["executavel"]
            for r in resultados
        )
    )

    tamanhos = sorted(
        set(
            r["tamanho"]
            for r in resultados
        )
    )

    def caminho_relativo(caminho):
        return (
            caminho.relative_to(
                diretorio
            )
            .as_posix()
        )

    with open(
        arquivo_saida,
        "w",
        encoding="utf-8"
    ) as f:

        # ----------------------------------------------------
        # Preâmbulo
        # ----------------------------------------------------

        f.write(
r"""\documentclass[11pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazil]{babel}

\usepackage{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{float}
\usepackage{siunitx}
\usepackage{hyperref}

\geometry{
    margin=2.5cm
}

\title{Relatório de Análise de Desempenho}
\author{}
\date{}

\begin{document}

\maketitle

"""
        )

        # ----------------------------------------------------
        # Identificação
        # ----------------------------------------------------

        f.write(
            "\\section{Identificação da análise}\n\n"
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
            "Arquivo de dados: & "
            r"\texttt{coleta.csv}"
            + r" \\"
            + "\n"
        )

        f.write(
            "Executáveis: & "
            + ", ".join(
                r"\texttt{"
                + escapar_latex(e)
                + "}"
                for e in executaveis
            )
            + r" \\"
            + "\n"
        )

        f.write(
            "Tamanhos analisados: & "
            + ", ".join(
                str(t)
                for t in tamanhos
            )
            + r" \\"
            + "\n"
        )

        f.write(
            "Bootstrap: & "
            f"{NUM_BOOTSTRAP} reamostragens"
            + r" \\"
            + "\n"
        )

        f.write(
            "\\end{tabular}\n\n"
        )

        f.write(
            "\\subsection*{Linha de comando}\n\n"
        )

        f.write(
            "\\begin{verbatim}\n"
        )

        f.write(
            linha_comando
            + "\n"
        )

        f.write(
            "\\end{verbatim}\n\n"
        )

        # ----------------------------------------------------
        # Metodologia
        # ----------------------------------------------------

        f.write(
r"""\section{Metodologia de análise}

Para cada combinação entre executável e tamanho de problema,
as observações foram analisadas de forma independente. Foram
calculadas medidas de tendência central, dispersão e forma da
distribuição. A precisão da estimativa da média foi caracterizada
por um intervalo de confiança de 95\% baseado na distribuição
$t$ de Student e por um intervalo de confiança bootstrap
percentual.

A presença de possíveis valores discrepantes foi verificada pelo
critério de $1{,}5\times IQR$. Esses valores foram identificados,
mas não removidos da análise.

Também foram avaliadas a existência de tendência temporal nas
observações, a autocorrelação entre execuções e a evolução da
média acumulada.

"""
        )

        # ----------------------------------------------------
        # Dispersão
        # ----------------------------------------------------

        f.write(
            "\\section{Dispersão temporal das execuções}\n\n"
        )

        f.write(
r"""\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\textwidth]{dispersao.jpg}
    \caption{Tempos observados em função da ordem global de execução.}
\end{figure}

"""
        )

        # ----------------------------------------------------
        # Boxplot
        # ----------------------------------------------------

        f.write(
            "\\section{Distribuição dos tempos}\n\n"
        )

        f.write(
r"""\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\textwidth]{boxplot.jpg}
    \caption{Boxplots dos tempos observados em cada caso experimental.}
\end{figure}

"""
        )

        # ----------------------------------------------------
        # Estatísticas centrais
        # ----------------------------------------------------

        f.write(
            "\\section{Estatísticas descritivas}\n\n"
        )

        f.write(
r"""{\tiny\begin{longtable}{
    l
    r
    r
    r
    r
    r
    r
    r
}
\toprule
Executável &
Tamanho &
$n$ &
Média &
Mediana &
Aparada &
DP &
CV (\%) \\
\midrule
\endhead
"""
        )

        for r in resultados:

            f.write(
                escapar_latex(
                    r["executavel"]
                )
                + " & "
                + str(
                    r["tamanho"]
                )
                + " & "
                + str(
                    r["n"]
                )
                + " & "
                + f"{r['media_ms']:.6f}"
                + " & "
                + f"{r['mediana_ms']:.6f}"
                + " & "
                + f"{r['media_aparada_ms']:.6f}"
                + " & "
                + f"{r['desvio_ms']:.6f}"
                + " & "
                + f"{r['cv'] * 100:.2f}"
                + r" \\"
                + "\n"
            )

        f.write(
r"""\bottomrule
\end{longtable}}

"""
        )

        # ----------------------------------------------------
        # Quartis
        # ----------------------------------------------------

        f.write(
            "\\subsection{Quartis, amplitude e valores extremos}\n\n"
        )

        f.write(
r"""{\tiny\begin{longtable}{
    l
    r
    r
    r
    r
    r
    r
}
\toprule
Executável &
Tamanho &
Mínimo &
Q1 &
Q3 &
Máximo &
IQR \\
\midrule
\endhead
"""
        )

        for r in resultados:

            f.write(
                escapar_latex(
                    r["executavel"]
                )
                + " & "
                + str(
                    r["tamanho"]
                )
                + " & "
                + f"{r['minimo_ms']:.6f}"
                + " & "
                + f"{r['q1_ms']:.6f}"
                + " & "
                + f"{r['q3_ms']:.6f}"
                + " & "
                + f"{r['maximo_ms']:.6f}"
                + " & "
                + f"{r['iqr_ms']:.6f}"
                + r" \\"
                + "\n"
            )

        f.write(
r"""\bottomrule
\end{longtable}}

"""
        )

        # ----------------------------------------------------
        # Assimetria e outliers
        # ----------------------------------------------------

        f.write(
            "\\subsection{Forma da distribuição e valores discrepantes}\n\n"
        )

        f.write(
r"""{\tiny\begin{longtable}{
    l
    r
    r
    r
    r
    r
}
\toprule
Executável &
Tamanho &
Assimetria &
Curtose &
Outliers &
Outliers (\%) \\
\midrule
\endhead
"""
        )

        for r in resultados:

            f.write(
                escapar_latex(
                    r["executavel"]
                )
                + " & "
                + str(
                    r["tamanho"]
                )
                + " & "
                + f"{r['assimetria']:.3f}"
                + " & "
                + f"{r['curtose_excesso']:.3f}"
                + " & "
                + str(
                    r["num_outliers"]
                )
                + " & "
                + f"{r['percentual_outliers']:.2f}"
                + r" \\"
                + "\n"
            )

        f.write(
r"""\bottomrule
\end{longtable}}

Os valores identificados como possíveis outliers foram mantidos
nas estatísticas. O arquivo \texttt{outliers.csv} permite localizar
cada uma dessas observações na coleta original.

"""
        )

        # ----------------------------------------------------
        # IC
        # ----------------------------------------------------

        f.write(
            "\\section{Precisão da estimativa da média}\n\n"
        )

        f.write(
r"""A tabela apresenta dois intervalos de confiança de 95\% para a
média: o primeiro obtido pela distribuição $t$ de Student e o
segundo pelo procedimento bootstrap. As margens são expressas
como a semilargura do respectivo intervalo em relação à média.

{\tiny\begin{longtable}{
    l
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
Executável &
Tamanho &
Média &
$t$ inf. &
$t$ sup. &
Margem $t$ &
Boot. inf. &
Boot. sup. &
Margem boot. \\
\midrule
\endhead
"""
        )

        for r in resultados:

            f.write(
                escapar_latex(
                    r["executavel"]
                )
                + " & "
                + str(
                    r["tamanho"]
                )
                + " & "
                + f"{r['media_ms']:.6f}"
                + " & "
                + f"{r['ic_t_inf']:.6f}"
                + " & "
                + f"{r['ic_t_sup']:.6f}"
                + " & "
                + f"{r['margem_t'] * 100:.2f}\\%"
                + " & "
                + f"{r['ic_boot_inf']:.6f}"
                + " & "
                + f"{r['ic_boot_sup']:.6f}"
                + " & "
                + f"{r['margem_boot'] * 100:.2f}\\%"
                + r" \\"
                + "\n"
            )

        f.write(
r"""\bottomrule
\end{longtable}}

"""
        )

        # ----------------------------------------------------
        # Normalidade
        # ----------------------------------------------------

        f.write(
            "\\section{Forma das distribuições e normalidade}\n\n"
        )

        f.write(
r"""O teste de Jarque--Bera é apresentado apenas como diagnóstico
complementar da forma das distribuições. A interpretação não deve
ser reduzida a uma classificação mecânica de ``normal'' ou
``não normal'', devendo ser considerada conjuntamente com os
histogramas e gráficos Q--Q.

{\tiny\begin{longtable}{lrrrr}
\toprule
Executável &
Tamanho &
JB &
$p$ &
Observações \\
\midrule
\endhead
"""
        )

        for r in resultados:

            if r["jarque_bera_p"] < 0.05:
                diagnostico = (
                    "evidência contra normalidade"
                )
            else:
                diagnostico = (
                    "sem evidência forte contra normalidade"
                )

            f.write(
                escapar_latex(
                    r["executavel"]
                )
                + " & "
                + str(
                    r["tamanho"]
                )
                + " & "
                + f"{r['jarque_bera']:.3f}"
                + " & "
                + f"{r['jarque_bera_p']:.4f}"
                + " & "
                + escapar_latex(
                    diagnostico
                )
                + r" \\"
                + "\n"
            )

        f.write(
r"""\bottomrule
\end{longtable}}

"""
        )

        # ----------------------------------------------------
        # Histogramas e QQ
        # ----------------------------------------------------

        for r in resultados:

            chave = (
                r["executavel"],
                r["tamanho"]
            )

            hist = (
                arquivos_histogramas.get(
                    chave
                )
            )

            qq = (
                arquivos_qq.get(
                    chave
                )
            )

            if hist is None or qq is None:
                continue

            f.write(
                "\\subsection{"
                + escapar_latex(
                    r["executavel"]
                )
                + " -- tamanho "
                + str(
                    r["tamanho"]
                )
                + "}\n\n"
            )

            f.write(
r"""\begin{figure}[H]
    \centering
"""
            )

            f.write(
                "    \\includegraphics"
                "[width=0.75\\textwidth]{"
                + caminho_relativo(hist)
                + "}\n"
            )

            f.write(
                "    \\caption{Histograma dos tempos.}\n"
                "\\end{figure}\n\n"
            )

            f.write(
r"""\begin{figure}[H]
    \centering
"""
            )

            f.write(
                "    \\includegraphics"
                "[width=0.75\\textwidth]{"
                + caminho_relativo(qq)
                + "}\n"
            )

            f.write(
                "    \\caption{Gráfico Q--Q.}\n"
                "\\end{figure}\n\n"
            )

        # ----------------------------------------------------
        # Tendência temporal
        # ----------------------------------------------------

        f.write(
            "\\section{Estabilidade temporal}\n\n"
        )

        f.write(
r"""A existência de uma tendência sistemática no decorrer da coleta
foi examinada por regressão linear do tempo em função da ordem de
execução e pelas correlações de Pearson e Spearman.

{\tiny\begin{longtable}{lrrrrr}
\toprule
Executável &
Tamanho &
Inclinação &
$R^2$ &
Pearson &
Spearman \\
\midrule
\endhead
"""
        )

        for r in resultados:

            f.write(
                escapar_latex(
                    r["executavel"]
                )
                + " & "
                + str(
                    r["tamanho"]
                )
                + " & "
                + f"{r['tendencia_slope']:.10f}"
                + " & "
                + f"{r['tendencia_r2']:.4f}"
                + " & "
                + f"{r['correlacao_pearson']:.4f}"
                + " & "
                + f"{r['correlacao_spearman']:.4f}"
                + r" \\"
                + "\n"
            )

        f.write(
r"""\bottomrule
\end{longtable}}

"""
        )

        # ----------------------------------------------------
        # Autocorrelação
        # ----------------------------------------------------

        f.write(
            "\\subsection{Autocorrelação}\n\n"
        )

        f.write(
r"""{\tiny\begin{longtable}{lrrr}
\toprule
Executável &
Tamanho &
Lag &
Autocorrelação \\
\midrule
\endhead
"""
        )

        for r in autocorrelacoes:

            f.write(
                escapar_latex(
                    r["executavel"]
                )
                + " & "
                + str(
                    r["tamanho"]
                )
                + " & "
                + str(
                    r["lag"]
                )
                + " & "
                + f"{r['autocorrelacao']:.4f}"
                + r" \\"
                + "\n"
            )

        f.write(
r"""\bottomrule
\end{longtable}}

"""
        )

        # ----------------------------------------------------
        # Convergência
        # ----------------------------------------------------

        f.write(
            "\\section{Convergência da média}\n\n"
        )

        f.write(
            "Os gráficos seguintes mostram a evolução "
            "da média acumulada à medida que novas "
            "observações são incorporadas.\n\n"
        )

        for r in resultados:

            chave = (
                r["executavel"],
                r["tamanho"]
            )

            figura = (
                arquivos_convergencia.get(
                    chave
                )
            )

            if figura is None:
                continue

            f.write(
r"""\begin{figure}[H]
    \centering
"""
            )

            f.write(
                "    \\includegraphics"
                "[width=0.75\\textwidth]{"
                + caminho_relativo(figura)
                + "}\n"
            )

            f.write(
                "    \\caption{Convergência da média -- "
                + escapar_latex(
                    r["executavel"]
                )
                + ", tamanho "
                + str(
                    r["tamanho"]
                )
                + ".}\n"
            )

            f.write(
                "\\end{figure}\n\n"
            )

        # ----------------------------------------------------
        # Síntese automática conservadora
        # ----------------------------------------------------

        f.write(
            "\\section{Síntese dos resultados}\n\n"
        )

        for r in resultados:

            f.write(
                "\\subsection{"
                + escapar_latex(
                    r["executavel"]
                )
                + " -- tamanho "
                + str(
                    r["tamanho"]
                )
                + "}\n\n"
            )

            f.write(
                "O tempo médio observado foi de "
                f"{r['media_ms']:.6f} ms"
                ", enquanto a mediana foi de "
                f"{r['mediana_ms']:.6f} ms"
                " e a média aparada em 10\\% foi de "
                f"{r['media_aparada_ms']:.6f} ms. "
            )

            f.write(
                "O coeficiente de variação foi de "
                f"{r['cv'] * 100:.2f}\\%. "
            )

            f.write(
                "O intervalo de confiança de 95\\% "
                "baseado na distribuição $t$ foi "
                f"[{r['ic_t_inf']:.6f}; "
                f"{r['ic_t_sup']:.6f}] ms"
                ", com margem relativa de "
                f"{r['margem_t'] * 100:.2f}\\%. "
            )

            f.write(
                "O bootstrap produziu o intervalo "
                f"[{r['ic_boot_inf']:.6f}; "
                f"{r['ic_boot_sup']:.6f}] ms"
                ", com margem relativa de "
                f"{r['margem_boot'] * 100:.2f}\\%. "
            )

            diferenca_centrais = (
                abs(
                    r["media_ms"]
                    - r["mediana_ms"]
                )
                / r["media_ms"]
                if r["media_ms"] != 0
                else 0.0
            )

            if diferenca_centrais <= 0.05:

                f.write(
                    "A proximidade entre média e mediana "
                    "indica que essas duas medidas fornecem "
                    "descrições semelhantes da tendência "
                    "central. "
                )

            else:

                f.write(
                    "A diferença entre média e mediana "
                    "sugere que a forma da distribuição "
                    "deve ser considerada ao interpretar "
                    "a média. "
                )

            if r["num_outliers"] > 0:

                f.write(
                    f"Foram identificados "
                    f"{r['num_outliers']} possíveis "
                    "valores discrepantes pelo critério "
                    "$1{,}5\\times IQR$. "
                )

            else:

                f.write(
                    "Não foram identificados possíveis "
                    "valores discrepantes pelo critério "
                    "$1{,}5\\times IQR$. "
                )

            f.write(
                "\n\n"
            )

        # ----------------------------------------------------
        # Final
        # ----------------------------------------------------

        f.write(
r"""\section{Arquivos associados}

Os dados e resultados utilizados neste relatório estão preservados
no mesmo diretório:

\begin{itemize}
    \item \texttt{coleta.csv}: dados brutos;
    \item \texttt{estatisticas.csv}: estatísticas calculadas;
    \item \texttt{outliers.csv}: possíveis valores discrepantes;
    \item \texttt{autocorrelacao.csv}: coeficientes de autocorrelação;
    \item \texttt{analise.py}: versão do programa de análise utilizada.
\end{itemize}

\end{document}
"""
        )

    return arquivo_saida


# ============================================================
# Programa principal
# ============================================================

def main():

    if len(sys.argv) < 3:

        print(
            f"Uso: {sys.argv[0]} "
            "<coleta.csv> "
            "<tamanho1> [tamanho2 ...]"
        )

        sys.exit(1)

    arquivo_csv = Path(
        sys.argv[1]
    )

    try:

        tamanhos = {
            int(valor)
            for valor in sys.argv[2:]
        }

    except ValueError:

        print(
            "Erro: os tamanhos devem ser inteiros.",
            file=sys.stderr
        )

        sys.exit(1)

    try:

        # ----------------------------------------------------
        anunciar(
            "1. Criação do registro da análise"
        )

        (
            diretorio,
            data_analise
        ) = criar_diretorio_registro(
            arquivo_csv
        )

        print(
            f"Diretório criado: {diretorio}"
        )

        print(
            "Cópia dos dados brutos: "
            f"{diretorio / 'coleta.csv'}"
        )

        # ----------------------------------------------------
        anunciar(
            "2. Leitura e preparação dos dados"
        )

        dados = ler_dados(
            arquivo_csv
        )

        dados = filtrar_tamanhos(
            dados,
            tamanhos
        )

        if not dados:

            raise ValueError(
                "Nenhum dado encontrado "
                "para os tamanhos informados."
            )

        casos = obter_casos(
            dados
        )

        print(
            f"{len(dados)} observações consideradas."
        )

        print(
            f"{len(casos)} casos experimentais."
        )

        # ----------------------------------------------------
        anunciar(
            "3. Análise de dispersão temporal"
        )

        arquivo_dispersao = (
            diretorio
            / "dispersao.jpg"
        )

        gerar_grafico_dispersao(
            dados,
            arquivo_dispersao
        )

        print(
            f"Gerado: {arquivo_dispersao}"
        )

        # ----------------------------------------------------
        anunciar(
            "4. Análise por boxplot"
        )

        arquivo_boxplot = (
            diretorio
            / "boxplot.jpg"
        )

        gerar_boxplot(
            casos,
            arquivo_boxplot
        )

        print(
            f"Gerado: {arquivo_boxplot}"
        )

        # ----------------------------------------------------
        anunciar(
            "5. Histogramas das distribuições"
        )

        diretorio_histogramas = (
            diretorio
            / "histogramas"
        )

        arquivos_histogramas = \
            gerar_histogramas(
                casos,
                diretorio_histogramas
            )

        print(
            f"Gerados em: "
            f"{diretorio_histogramas}"
        )

        # ----------------------------------------------------
        anunciar(
            "6. Análise gráfica de normalidade - Q-Q plots"
        )

        diretorio_qq = (
            diretorio
            / "qqplots"
        )

        arquivos_qq = \
            gerar_qqplots(
                casos,
                diretorio_qq
            )

        print(
            f"Gerados em: {diretorio_qq}"
        )

        # ----------------------------------------------------
        anunciar(
            "7. Estatísticas descritivas e inferenciais"
        )

        resultados = \
            calcular_estatisticas(
                casos
            )

        imprimir_estatisticas(
            resultados
        )

        arquivo_estatisticas = (
            diretorio
            / "estatisticas.csv"
        )

        salvar_estatisticas(
            resultados,
            arquivo_estatisticas
        )

        print()
        print(
            f"Gerado: {arquivo_estatisticas}"
        )

        # ----------------------------------------------------
        anunciar(
            "8. Identificação de possíveis outliers"
        )

        arquivo_outliers = (
            diretorio
            / "outliers.csv"
        )

        salvar_outliers(
            casos,
            arquivo_outliers
        )

        print(
            f"Gerado: {arquivo_outliers}"
        )

        # ----------------------------------------------------
        anunciar(
            "9. Análise de normalidade por Jarque-Bera"
        )

        for r in resultados:

            print(
                f"{r['executavel']}, "
                f"n={r['tamanho']}: "
                f"JB={r['jarque_bera']:.4f}, "
                f"p={r['jarque_bera_p']:.4f}"
            )

        # ----------------------------------------------------
        anunciar(
            "10. Análise de tendência temporal"
        )

        for r in resultados:

            print(
                f"{r['executavel']}, "
                f"n={r['tamanho']}: "
                f"slope="
                f"{r['tendencia_slope']:.10f} "
                f"ms/ordem, "
                f"R²="
                f"{r['tendencia_r2']:.4f}, "
                f"Pearson="
                f"{r['correlacao_pearson']:.4f}, "
                f"Spearman="
                f"{r['correlacao_spearman']:.4f}"
            )

        # ----------------------------------------------------
        anunciar(
            "11. Análise de autocorrelação"
        )

        arquivo_autocorrelacao = (
            diretorio
            / "autocorrelacao.csv"
        )

        autocorrelacoes = \
            salvar_autocorrelacao(
                casos,
                arquivo_autocorrelacao
            )

        print(
            f"Gerado: "
            f"{arquivo_autocorrelacao}"
        )

        # ----------------------------------------------------
        anunciar(
            "12. Análise da convergência da média"
        )

        diretorio_convergencia = (
            diretorio
            / "convergencia"
        )

        arquivos_convergencia = \
            gerar_convergencia(
                casos,
                diretorio_convergencia
            )

        print(
            f"Gerados em: "
            f"{diretorio_convergencia}"
        )

        # ----------------------------------------------------
        anunciar(
            "13. Geração do relatório LaTeX"
        )

        linha_comando = (
            " ".join(
                sys.argv
            )
        )

        arquivo_relatorio = \
            gerar_relatorio_latex(
                diretorio,
                data_analise,
                linha_comando,
                resultados,
                autocorrelacoes,
                arquivos_histogramas,
                arquivos_qq,
                arquivos_convergencia
            )

        print(
            f"Gerado: {arquivo_relatorio}"
        )

        # ----------------------------------------------------
        anunciar(
            "Análise concluída"
        )

        print(
            f"Todos os resultados estão em:\n"
            f"    {diretorio}"
        )

        print()
        print(
            "Arquivos principais:"
        )

        print(
            "    coleta.csv"
        )

        print(
            "    analise.py"
        )

        print(
            "    relatorio.tex"
        )

        print(
            "    estatisticas.csv"
        )

        print(
            "    outliers.csv"
        )

        print(
            "    autocorrelacao.csv"
        )

        print(
            "    dispersao.jpg"
        )

        print(
            "    boxplot.jpg"
        )

        print(
            "    histogramas/"
        )

        print(
            "    qqplots/"
        )

        print(
            "    convergencia/"
        )

    except FileNotFoundError:

        print(
            f"Erro: arquivo "
            f"'{arquivo_csv}' não encontrado.",
            file=sys.stderr
        )

        sys.exit(1)

    except Exception as erro:

        print(
            f"Erro: {erro}",
            file=sys.stderr
        )

        sys.exit(1)


if __name__ == "__main__":
    main()
