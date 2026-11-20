import hashlib
from pathlib import Path
import sqlite3

ARQUIVO_DB = Path(__file__).resolve().parent / "db_python.db"


def criar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


def conectar():
    conexao = sqlite3.connect(ARQUIVO_DB)
    cursor = conexao.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    return conexao, cursor


def inicializar_tabelas():
    conexao, cursor = conectar()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Estabelecimento (
            id_est INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            nome_est VARCHAR(50) NOT NULL,
            local VARCHAR(50) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Cozinha (
            id_coz INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            nome_coz VARCHAR(50) NOT NULL,
            local VARCHAR(50) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Oferta_Alimento (
            id_oferta INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            id_est INTEGER NOT NULL,
            produto VARCHAR(50) NOT NULL,
            quantidade INTEGER NOT NULL,
            validade DATE NOT NULL,
            motivo_descarte VARCHAR(100),
            FOREIGN KEY (id_est) REFERENCES Estabelecimento(id_est)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Necessidade_Cozinha (
            id_necessidade INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            id_coz INTEGER NOT NULL,
            produto VARCHAR(50) NOT NULL,
            quantidade INTEGER NOT NULL,
            data_limite DATE NOT NULL,
            FOREIGN KEY (id_coz) REFERENCES Cozinha(id_coz)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Log_Ofertas (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem TEXT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_log_ofertas
        AFTER INSERT ON Oferta_Alimento
        FOR EACH ROW
        BEGIN
            INSERT INTO Log_Ofertas (mensagem)
            VALUES (
                'Nova oferta adicionada - ID Estabelecimento: '
                || NEW.id_est || ' | Produto: ' || NEW.produto
            );
        END
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            perfil TEXT NOT NULL CHECK (perfil IN ('mercado', 'cozinha')),
            id_entidade INTEGER NOT NULL
        )
    """)

    conexao.commit()
    conexao.close()


def obter_ou_criar_entidade(cursor, perfil, nome, local):
    if perfil == "mercado":
        cursor.execute(
            "SELECT id_est FROM Estabelecimento WHERE nome_est = ? AND local = ?",
            (nome, local),
        )
        linha = cursor.fetchone()
        if linha:
            return linha[0]

        cursor.execute(
            "INSERT INTO Estabelecimento (nome_est, local) VALUES (?, ?)",
            (nome, local),
        )
        return cursor.lastrowid

    if perfil == "cozinha":
        cursor.execute(
            "SELECT id_coz FROM Cozinha WHERE nome_coz = ? AND local = ?",
            (nome, local),
        )
        linha = cursor.fetchone()
        if linha:
            return linha[0]

        cursor.execute(
            "INSERT INTO Cozinha (nome_coz, local) VALUES (?, ?)",
            (nome, local),
        )
        return cursor.lastrowid

    return None


def cadastrar_usuario(usuario, senha, perfil, nome_entidade, local_entidade):
    conexao, cursor = conectar()
    senha_criptografada = criar_hash(senha)
    try:
        id_entidade = obter_ou_criar_entidade(
            cursor, perfil, nome_entidade, local_entidade
        )
        cursor.execute(
            """
            INSERT INTO usuarios (usuario, senha_hash, perfil, id_entidade)
            VALUES (?, ?, ?, ?)
            """,
            (usuario, senha_criptografada, perfil, id_entidade),
        )
        conexao.commit()
        print(f"Cadastro concluído! ID vinculado: {id_entidade}")
        return True
    except sqlite3.IntegrityError:
        conexao.rollback()
        print("Esse nome de usuário já existe. Voltando ao menu inicial...")
        return False
    except sqlite3.Error as erro:
        conexao.rollback()
        print("Erro no banco durante o cadastro:", erro)
        return False
    finally:
        conexao.close()


def fazer_login(usuario, senha):
    conexao, cursor = conectar()
    try:
        cursor.execute(
            "SELECT senha_hash, perfil, id_entidade FROM usuarios WHERE usuario = ?",
            (usuario,),
        )
        linha = cursor.fetchone()
        if linha is None:
            return False, None, None

        senha_salva, perfil, id_entidade = linha
        if criar_hash(senha) == senha_salva:
            return True, perfil, id_entidade

        return False, None, None
    except sqlite3.Error as erro:
        print("Erro ao consultar usuário:", erro)
        return False, None, None
    finally:
        conexao.close()


def consultar_cruzamento(cursor):
    cursor.execute("""
        SELECT
            e.nome_est AS Mercado,
            o.produto AS Produto_Disponivel,
            o.quantidade AS Qtd_Oferta,
            o.validade AS Validade,
            c.nome_coz AS Cozinha_Precisa,
            n.quantidade AS Qtd_Necessaria,
            n.data_limite AS Data_Limite
        FROM Oferta_Alimento o
        INNER JOIN Estabelecimento e ON o.id_est = e.id_est
        INNER JOIN Necessidade_Cozinha n ON o.produto = n.produto
        INNER JOIN Cozinha c ON n.id_coz = c.id_coz
    """)
    linhas = cursor.fetchall()
    if not linhas:
        print("Nenhum cruzamento encontrado entre ofertas e necessidades.")
    else:
        for r in linhas:
            print(
                f"Mercado: {r[0]} | Produto: {r[1]} | Oferta: {r[2]} (Val: {r[3]}) "
                f"-> Cozinha: {r[4]} | Necessidade: {r[5]} (Limite: {r[6]})"
            )


def menu_mercado(id_est):
    conexao, cursor = conectar()

    try:
        while True:
            print(f"\n--- INVENTÁRIO MERCADO (ID Estabelecimento: {id_est}) ---")
            print("1 - Consultar minhas ofertas")
            print("2 - Adicionar oferta")
            print("3 - Alterar quantidade da oferta")
            print("4 - Excluir oferta")
            print("5 - Ver cruzamento com cozinhas")
            print("0 - Sair do inventário")
            opcao = input("Escolha: ").strip()

            if opcao == "1":
                cursor.execute(
                    """
                    SELECT id_oferta, produto, quantidade, validade, motivo_descarte
                    FROM Oferta_Alimento
                    WHERE id_est = ?
                    """,
                    (id_est,),
                )
                itens = cursor.fetchall()
                if not itens:
                    print("Nenhuma oferta cadastrada.")
                else:
                    for item in itens:
                        print(
                            f"ID Oferta: {item[0]} | Produto: {item[1]} | "
                            f"Qtd: {item[2]} | Validade: {item[3]} | Motivo: {item[4]}"
                        )

            elif opcao == "2":
                try:
                    produto = input("Produto: ").strip()
                    quantidade = int(input("Quantidade: ").strip())
                    validade = input("Validade (AAAA-MM-DD): ").strip()
                    motivo_descarte = input("Motivo do descarte (opcional): ").strip() or None
                    cursor.execute(
                        """
                        INSERT INTO Oferta_Alimento
                            (id_est, produto, quantidade, validade, motivo_descarte)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (id_est, produto, quantidade, validade, motivo_descarte),
                    )
                    conexao.commit()
                    print("Oferta adicionada com sucesso.")
                except ValueError:
                    print("Quantidade inválida. Digite um número inteiro.")
                except sqlite3.Error as erro:
                    conexao.rollback()
                    print("Erro ao inserir oferta:", erro)

            elif opcao == "3":
                try:
                    id_oferta = int(input("ID da oferta para alterar: ").strip())
                    nova_qtd = int(input("Nova quantidade: ").strip())
                    cursor.execute(
                        """
                        UPDATE Oferta_Alimento
                        SET quantidade = ?
                        WHERE id_oferta = ? AND id_est = ?
                        """,
                        (nova_qtd, id_oferta, id_est),
                    )
                    conexao.commit()
                    print("Ofertas alteradas:", cursor.rowcount)
                except ValueError:
                    print("ID ou quantidade inválidos. Digite números inteiros.")
                except sqlite3.Error as erro:
                    conexao.rollback()
                    print("Erro ao alterar oferta:", erro)

            elif opcao == "4":
                try:
                    id_oferta = int(input("ID da oferta para excluir: ").strip())
                    cursor.execute(
                        "DELETE FROM Oferta_Alimento WHERE id_oferta = ? AND id_est = ?",
                        (id_oferta, id_est),
                    )
                    conexao.commit()
                    print("Ofertas excluídas:", cursor.rowcount)
                except ValueError:
                    print("ID inválido. Digite um número inteiro.")
                except sqlite3.Error as erro:
                    conexao.rollback()
                    print("Erro ao excluir oferta:", erro)

            elif opcao == "5":
                consultar_cruzamento(cursor)

            elif opcao == "0":
                print("Saindo do inventário...")
                break
            else:
                print("Opção inválida.")
    finally:
        conexao.close()


def menu_cozinha(id_coz):
    conexao, cursor = conectar()

    try:
        while True:
            print(f"\n--- INVENTÁRIO COZINHA (ID Cozinha: {id_coz}) ---")
            print("1 - Consultar minhas necessidades")
            print("2 - Adicionar necessidade")
            print("3 - Alterar quantidade da necessidade")
            print("4 - Excluir necessidade")
            print("5 - Ver cruzamento com mercados")
            print("0 - Sair do inventário")
            opcao = input("Escolha: ").strip()

            if opcao == "1":
                cursor.execute(
                    """
                    SELECT id_necessidade, produto, quantidade, data_limite
                    FROM Necessidade_Cozinha
                    WHERE id_coz = ?
                    """,
                    (id_coz,),
                )
                itens = cursor.fetchall()
                if not itens:
                    print("Nenhuma necessidade cadastrada.")
                else:
                    for item in itens:
                        print(
                            f"ID Necessidade: {item[0]} | Produto: {item[1]} | "
                            f"Qtd: {item[2]} | Data limite: {item[3]}"
                        )

            elif opcao == "2":
                try:
                    produto = input("Produto: ").strip()
                    quantidade = int(input("Quantidade: ").strip())
                    data_limite = input("Data limite (AAAA-MM-DD): ").strip()
                    cursor.execute(
                        """
                        INSERT INTO Necessidade_Cozinha
                            (id_coz, produto, quantidade, data_limite)
                        VALUES (?, ?, ?, ?)
                        """,
                        (id_coz, produto, quantidade, data_limite),
                    )
                    conexao.commit()
                    print("Necessidade adicionada com sucesso.")
                except ValueError:
                    print("Quantidade inválida. Digite um número inteiro.")
                except sqlite3.Error as erro:
                    conexao.rollback()
                    print("Erro ao inserir necessidade:", erro)

            elif opcao == "3":
                try:
                    id_nec = int(input("ID da necessidade para alterar: ").strip())
                    nova_qtd = int(input("Nova quantidade: ").strip())
                    cursor.execute(
                        """
                        UPDATE Necessidade_Cozinha
                        SET quantidade = ?
                        WHERE id_necessidade = ? AND id_coz = ?
                        """,
                        (nova_qtd, id_nec, id_coz),
                    )
                    conexao.commit()
                    print("Necessidades alteradas:", cursor.rowcount)
                except ValueError:
                    print("ID ou quantidade inválidos. Digite números inteiros.")
                except sqlite3.Error as erro:
                    conexao.rollback()
                    print("Erro ao alterar necessidade:", erro)

            elif opcao == "4":
                try:
                    id_nec = int(input("ID da necessidade para excluir: ").strip())
                    cursor.execute(
                        "DELETE FROM Necessidade_Cozinha WHERE id_necessidade = ? AND id_coz = ?",
                        (id_nec, id_coz),
                    )
                    conexao.commit()
                    print("Necessidades excluídas:", cursor.rowcount)
                except ValueError:
                    print("ID inválido. Digite um número inteiro.")
                except sqlite3.Error as erro:
                    conexao.rollback()
                    print("Erro ao excluir necessidade:", erro)

            elif opcao == "5":
                consultar_cruzamento(cursor)

            elif opcao == "0":
                print("Saindo do inventário...")
                break
            else:
                print("Opção inválida.")
    finally:
        conexao.close()


def menu_acesso():
    while True:
        print("\n=== ACESSO AO SISTEMA ===")
        print("1 - Fazer login")
        print("2 - Primeiro cadastro")
        print("0 - Encerrar programa")
        acao = input("Escolha: ").strip()

        if acao == "1":
            usuario_digitado = input("Usuário: ").strip()
            senha_digitada = input("Senha: ").strip()

            if not usuario_digitado or not senha_digitada:
                print("Usuário e senha são obrigatórios. Voltando ao menu...")
                continue

            logou, perfil, id_entidade = fazer_login(usuario_digitado, senha_digitada)

            if not logou:
                print("Usuário ou senha inválidos. Voltando ao menu...")
                continue

            if perfil == "mercado":
                menu_mercado(id_entidade)
            elif perfil == "cozinha":
                menu_cozinha(id_entidade)
            else:
                print("Perfil não reconhecido. Voltando ao menu...")

        elif acao == "2":
            novo_usuario = input("Novo usuário: ").strip()
            nova_senha = input("Nova senha: ").strip()
            perfil = input("Perfil (mercado ou cozinha): ").strip().lower()

            if not novo_usuario or not nova_senha:
                print("Usuário e senha não podem ficar vazios. Voltando ao menu...")
                continue

            if perfil not in ("mercado", "cozinha"):
                print("Perfil inválido. Use 'mercado' ou 'cozinha'. Voltando ao menu...")
                continue

            nome_ent = input("Nome do estabelecimento/cozinha: ").strip()
            local_ent = input("Local/bairro: ").strip()

            if not nome_ent or not local_ent:
                print("Nome e local são obrigatórios. Voltando ao menu...")
                continue

            cadastrar_usuario(novo_usuario, nova_senha, perfil, nome_ent, local_ent)

        elif acao == "0":
            print("Programa encerrado.")
            break

        else:
            print("Opção inválida. Tente novamente.")


inicializar_tabelas()
menu_acesso()

