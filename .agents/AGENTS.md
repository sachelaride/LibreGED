# Regras de Negócio e Contexto do Projeto EduGED Libre

## Arquivos e Material Auxiliar
- O diretório `modelos/` localizado na raiz do projeto (e suas subpastas) contém documentos, arquivos de exemplo, imagens e recursos auxiliares úteis para o desenvolvimento e entendimento dos requisitos. 
- Os agentes devem lembrar e consultar esta pasta proativamente quando precisarem de material de apoio, layouts de referência ou exemplos do negócio.
- Esta pasta e seus arquivos são ignorados pelo Git e **nunca** devem ser enviados/commitados para o repositório remoto.

## Idioma do Código e Documentação
- **Português Obrigatório**: Toda a documentação (docstrings, README, etc.), mensagens de commit, mensagens de retorno de API, variáveis e **comentários** no código devem ser escritos em português do Brasil (pt-BR).
- Exceção apenas para palavras-chave da linguagem de programação, bibliotecas de terceiros ou protocolos padrão que exigem o uso do inglês. Variáveis de negócio devem preferencialmente adotar nomenclatura em português (ex: `documento_id` ao invés de `document_id`, sempre que possível e não quebrar padrões já definidos).

- **Seguran�a**: Nunca 'comitar' ou subir credenciais, senhas, chaves de API, ou arquivos .env para o controle de vers�o (Git). Garantir sempre que .env e similares estejam no .gitignore.
