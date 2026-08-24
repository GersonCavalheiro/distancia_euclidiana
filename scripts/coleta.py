#!/usr/bin/env python3

import argparse
import csv
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def executar_programa(executavel, tamanho):
    """
    Executa um programa no formato:

        executavel tamanho

    Espera uma saída:

        nome,tamanho,tempo

    Exemplo:

        gerson,1000000,1.074869
    """

    comando = [executavel, str(tamanho)]

    resultado = subprocess.run(
        comando,
        capture_output=True,
        text=True
    )

    return comando, resultado


def interpretar_saida(saida, tamanho_esperado):
    """
    Interpreta a saída produzida pelo executável.

    Formato esperado:

        nome,tamanho,tempo
    """

    linha = saida.strip()

    campos = linha.split(",")

    if len(campos) != 3:
        raise ValueError(
            f"Saída inválida: '{linha}'"
        )

    nome = campos[0].strip()
    tamanho = int(campos[1])
    tempo = float(campos[2])

    if tamanho != tamanho_esperado:
        raise ValueError(
            f"Tamanho retornado ({tamanho}) diferente "
            f"do solicitado ({tamanho_esperado})"
        )

    return nome, tamanho, tempo


def registrar_log(arquivo_log, mensagem):
    agora = datetime.now().isoformat(timespec="milliseconds")

    arquivo_log.write(
        f"[{agora}] {mensagem}\n"
    )

    arquivo_log.flush()


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Coleta dados de desempenho executando, de forma "
            "intercalada, o produto cartesiano entre executáveis "
            "e tamanhos de problema."
        )
    )

    parser.add_argument(
        "n",
        type=int,
        help="Número de repetições de cada caso experimental"
    )

    parser.add_argument(
        "--executaveis",
        nargs="+",
        required=True,
        help="Lista de executáveis"
    )

    parser.add_argument(
        "--tamanhos",
        nargs="+",
        type=int,
        required=True,
        help="Lista de tamanhos do problema"
    )

    parser.add_argument(
        "--saida",
        default="coleta.csv",
        help="Arquivo CSV de saída (padrão: coleta.csv)"
    )

    parser.add_argument(
        "--log",
        default="coleta.log",
        help="Arquivo de log (padrão: coleta.log)"
    )

    args = parser.parse_args()

    if args.n <= 0:
        print(
            "Erro: n deve ser maior que zero.",
            file=sys.stderr
        )
        sys.exit(1)

    for tamanho in args.tamanhos:
        if tamanho <= 0:
            print(
                "Erro: todos os tamanhos devem ser maiores que zero.",
                file=sys.stderr
            )
            sys.exit(1)

    # --------------------------------------------------------
    # Produto cartesiano:
    #
    #     executáveis × tamanhos
    #
    # Cada elemento representa um caso experimental.
    # --------------------------------------------------------

    casos = [
        (executavel, tamanho)
        for executavel in args.executaveis
        for tamanho in args.tamanhos
    ]

    total_casos = len(casos)
    total_execucoes = args.n * total_casos

    caminho_csv = Path(args.saida)
    caminho_log = Path(args.log)

    with (
        caminho_csv.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as arquivo_csv,

        caminho_log.open(
            "w",
            encoding="utf-8"
        ) as arquivo_log
    ):

        escritor = csv.writer(arquivo_csv, lineterminator="\n")

        escritor.writerow([
            "rodada",
            "ordem",
            "executavel",
            "nome",
            "tamanho",
            "tempo_ms"
        ])

        registrar_log(
            arquivo_log,
            "Início da coleta"
        )

        registrar_log(
            arquivo_log,
            f"Repetições por caso: {args.n}"
        )

        registrar_log(
            arquivo_log,
            f"Executáveis: {args.executaveis}"
        )

        registrar_log(
            arquivo_log,
            f"Tamanhos: {args.tamanhos}"
        )

        registrar_log(
            arquivo_log,
            f"Número de casos por rodada: {total_casos}"
        )

        registrar_log(
            arquivo_log,
            f"Total previsto de execuções: {total_execucoes}"
        )

        ordem_global = 0

        # ----------------------------------------------------
        # Cada rodada contém exatamente uma execução de cada
        # combinação executável × tamanho.
        #
        # A ordem dos casos é embaralhada novamente a cada
        # rodada para evitar concentração temporal de um caso.
        # ----------------------------------------------------

        for rodada in range(1, args.n + 1):

            ordem_rodada = casos.copy()
            random.shuffle(ordem_rodada)

            registrar_log(
                arquivo_log,
                f"Início da rodada {rodada}/{args.n}"
            )

            for executavel, tamanho in ordem_rodada:

                ordem_global += 1

                comando, resultado = executar_programa(
                    executavel,
                    tamanho
                )

                comando_texto = " ".join(comando)

                registrar_log(
                    arquivo_log,
                    (
                        f"Execução {ordem_global}/{total_execucoes}: "
                        f"{comando_texto}"
                    )
                )

                if resultado.returncode != 0:

                    registrar_log(
                        arquivo_log,
                        (
                            f"ERRO: retorno={resultado.returncode}; "
                            f"stderr='{resultado.stderr.strip()}'"
                        )
                    )

                    continue

                try:
                    nome, tamanho_retornado, tempo = \
                        interpretar_saida(
                            resultado.stdout,
                            tamanho
                        )

                except Exception as erro:

                    registrar_log(
                        arquivo_log,
                        (
                            f"ERRO ao interpretar saída de "
                            f"'{comando_texto}': {erro}; "
                            f"stdout='{resultado.stdout.strip()}'"
                        )
                    )

                    continue

                escritor.writerow([
                    rodada,
                    ordem_global,
                    Path(executavel).name,
                    nome,
                    tamanho_retornado,
                    f"{tempo:.6f}"
                ])

                arquivo_csv.flush()

                registrar_log(
                    arquivo_log,
                    (
                        f"OK: nome={nome}; "
                        f"tamanho={tamanho_retornado}; "
                        f"tempo_ms={tempo:.6f}"
                    )
                )

            registrar_log(
                arquivo_log,
                f"Fim da rodada {rodada}/{args.n}"
            )

        registrar_log(
            arquivo_log,
            "Fim da coleta"
        )


if __name__ == "__main__":
    main()
