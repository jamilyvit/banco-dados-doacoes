# Sistema de Gestão de Doações de Alimentos 

## Sobre o Projeto
O projeto foi desenvolvido para um trabalho acadêmico com o objetivo de gerenciar alimentos que estão próprios para consumo, mas que por algum motivo não podem ser comercializados (como embalagens com defeito, validade próxima, entre outros), conciliando-os com as necessidades de instituições que dependem de doações (como cozinhas solidárias e orfanatos). O intuito principal é **reduzir o desperdício de alimentos** e **ajudar quem mais precisa** de forma prática e organizada. 
Além disso, a estrutura do banco de dados foi pensada com foco na escalabilidade: **as chaves primárias foram configuradas com autoincremento (`AUTOINCREMENT`) diretamente no SQLite**, facilitando a futura integração com um sistema de gestão de inventário desenvolvido em **Python**. Dessa forma, o banco de dados gerencia a integridade dos IDs de forma automatizada, preparando o terreno para aplicações externas consumirem e manipularem os dados com segurança.

## Tecnologias utilizadas
* **SQLite** (Gerenciador de banco de dados)
* **DB Browser for SQLite** (Ferramenta de manipulação)
* **SQL** (Scripts de criação, consultas e triggers)

## Funcionalidades
* Cadastro de estabelecimentos, cozinhas, ofertas e necessidades.
* Consultas avançadas utilizando **JOIN**.
* **Trigger de Auditoria:** Registro automático de logs para cada nova oferta cadastrada.


