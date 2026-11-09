# Comunidade Ativa — versão 3

Aplicação web acadêmica para registro e acompanhamento de ocorrências comunitárias.

## O que esta versão contém
- Cadastro de usuário e login.
- Senhas armazenadas com hash (não são salvas em texto puro).
- Cadastro de ocorrências com título, categoria, descrição e bairro.
- Uma foto opcional por ocorrência. Imagens JPG, PNG ou WEBP são convertidas para JPEG e redimensionadas para **600 × 600 pixels**.
- Limite de upload de 5 MB.
- Listagem pública e pesquisa por categoria/texto.
- Área "Minhas ocorrências".
- Cada usuário só pode excluir suas próprias ocorrências.
- Banco SQLite criado automaticamente na primeira execução.

## Requisitos
Python 3.10 ou superior.

## Executar no Windows
Abra o terminal na pasta extraída e execute:

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

Abra no navegador: http://127.0.0.1:5000

## Primeiro teste recomendado
1. Crie uma conta em **Criar conta**.
2. Entre com o e-mail e a senha.
3. Clique em **Nova ocorrência** e preencha os campos.
4. Anexe uma imagem para testar o redimensionamento.
5. Consulte **Minhas ocorrências** e abra o detalhe do relato.
6. Crie uma segunda conta e confirme que a área "Minhas ocorrências" mostra somente os registros da conta conectada.

## Estrutura
- `app.py`: rotas, autenticação, banco e upload de imagens.
- `templates/`: páginas HTML.
- `static/style.css`: estilos.
- `uploads/`: imagens enviadas (criada automaticamente).
- `comunidade_ativa.db`: banco SQLite (criado automaticamente).

## Observações importantes
- Esta é uma versão local para desenvolvimento e demonstração acadêmica, não uma implantação pronta para internet.
- Antes de publicar, configure uma `SECRET_KEY` forte por variável de ambiente, desative `debug=True`, use HTTPS e revise controles adicionais de segurança.
- O status inicial das ocorrências é "Aberta". Um painel administrativo e fluxo de atualização de status podem ser desenvolvidos na próxima etapa.
- Os resultados e testes descritos no relatório devem corresponder aos testes realmente executados pelo estudante.
