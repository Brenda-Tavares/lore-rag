# Lore

**RAG seguro para conhecimento de SRE.** Sistema de geração aumentada por recuperação que ingere
documentos operacionais, remove dados sensíveis antes do armazenamento e responde perguntas com
fontes citadas.

[English](README.md) · [Português](README.pt-BR.md) · [简体中文](README.zh-CN.md)

Autora: Brenda Tavares · Estado: MVP local, não implantado · QA: manual (§9) · Atualizado: 2026-10-17

> Projeto de portfólio. Todas as chaves ficam em um `.env` ignorado pelo git; nenhuma chave é
> commitada neste repositório.

---

## 1. O Problema

Conhecimento operacional — runbooks, procedimentos de incidentes, guias de troubleshooting —
vive em arquivos espalhados e na cabeça das pessoas. Quando um engenheiro de plantão precisa
de uma resposta durante um incidente, o tempo de busca é medido em minutos de indisponibilidade.

Ferramentas genéricas falham nesse caso por três motivos:

- **Busca por palavras-chave falha em recall difuso.** O engenheiro lembra do sintoma, não
  do comando ou título exatos.
- **Respostas de LLM puro não são auditáveis.** Um modelo consultado pela própria memória
  pode confabular comandos que não existem nos runbooks da instituição, e nada expõe isso.
- **Documentos operacionais contêm segredos.** Credenciais, tokens e hostnames aparecem em
  runbooks reais. Enviá-los para um índice externo, ou colá-los em uma interface de chat,
  os vaza.

Lore aborda os três de uma vez: recuperação semântica sobre os documentos da própria
instituição, respostas fundamentadas em contexto recuperado e devolvidas com citações, e
sanitização de dados sensíveis **antes** de qualquer coisa ser armazenada.

---

## 2. Racional de Design

Quatro restrições moldaram a arquitetura:

- **Auditabilidade sobre fluência.** Uma resposta sem fonte é um passivo em operações.
  Cada resposta devolve os chunks exatos nos quais foi fundamentada, e a UI os renderiza
  como citações. Quando a recuperação não encontra nada, o sistema diz isso em vez de
  improvisar.
- **Sanitização antes da persistência, não depois.** A remoção roda dentro do pipeline de
  ingestão, antes do chunking e do embedding. Um segredo que nunca entra no vector store
  não pode ser recuperado, ecoado ou vazado por nenhum componente posterior.
- **Isolamento por construção, não por convenção.** Multi-tenancy é forçado como filtro
  obrigatório em toda consulta vetorial, não como parâmetro opcional que um desenvolvedor
  possa esquecer. O tenant atual é um identificador fixo de desenvolvimento; autenticação
  está no roadmap (§10, §14).
- **Desenvolvimento sem infraestrutura, caminho de produção documentado.** O Qdrant roda em
  modo embutido (path local) para que o MVP não precise de nenhum serviço extra. O caminho
  de migração para um servidor Qdrant e Postgres gerenciado está documentado (§13) em vez
  de assumido silenciosamente.

---

## 3. A Solução

Um sistema de dois pipelines com interface trilíngue:

**Ingestão.** Upload → validação por allowlist de MIME → remoção de segredos/PII → chunking
em janela deslizante com overlap → embedding (OpenRouter, com cache em disco, batch e backoff
exponencial) → PostgreSQL (metadados de documento e chunk) + Qdrant (vetores com payload de
tenant).

**Recuperação.** Pergunta → mesmo modelo de embedding → busca vetorial filtrada por tenant →
top-5 chunks → montagem do prompt (instrução de fundamentação + contexto + pergunta) → LLM
Groq → resposta em Markdown mais fontes citadas.

**Interface.** Uma SPA React em PT-BR / EN / ZH-CN expõe upload e chat, renderiza Markdown
e citações, e nunca vê uma chave de API.

---

## 4. Stack Tecnológica

| Camada | Escolha | Por quê |
| --- | --- | --- |
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS 3 (+ plugin typography), axios, react-markdown, lucide-react | Interface de ferramenta SPA; TypeScript para segurança de contrato; Tailwind para um design system consistente sem biblioteca de componentes |
| Backend | FastAPI (Python 3.11), Pydantic Settings v2 | API assíncrona com validação tipada; settings resolvidas de um caminho explícito de arquivo env |
| Relacional | PostgreSQL, SQLAlchemy 2 (psycopg2) | Metadados de documento e chunk com integridade relacional |
| Vector store | Qdrant, modo embutido com path local | Desenvolvimento sem infraestrutura; filtros de payload permitem isolamento obrigatório por tenant; modo servidor documentado para produção |
| Embeddings | OpenRouter (`liquid/lfm-2.5-embedding-350m:free`) com cache em disco, batch e backoff | Tier gratuito com gasto limitado; cache remove chamadas repetidas; batch reduz número de requisições |
| LLM | Groq (`openai/gpt-oss-120b`) | Inferência de baixa latência para o caminho de chat |
| i18n | Dicionários inline (26 chaves × 3 idiomas), React Context, localStorage | Sem dependência de biblioteca; mesma abordagem zero-dependência usada em todo o portfólio da autora |

---

## 5. Arquitetura

```
INGESTÃO
browser ──multipart──▶ FastAPI ──▶ allowlist MIME ──▶ remoção ──▶ chunking
                              │
                              ▼
                  embedding (OpenRouter: cache / batch / backoff)
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
          PostgreSQL                 Qdrant (embutido)
     documentos, chunks           vetores + payload de tenant

RECUPERAÇÃO
browser ──pergunta──▶ FastAPI ──▶ embed da pergunta ──▶ busca Qdrant (filtro de tenant, top-5)
                              │
                              ▼
                 prompt = instrução de fundamentação + chunks + pergunta
                              │
                              ▼
                        LLM Groq ──▶ resposta (Markdown) + fontes
```

| Endpoint | Propósito |
| --- | --- |
| `POST /api/v1/documents/upload` | Ingestão multipart com validação e remoção |
| `POST /api/v1/ai/chat` | Resposta fundamentada com fontes citadas |
| `GET /health` | Probe de liveness |
| `GET /docs` | OpenAPI / Swagger UI |

---

## 6. Modelo de Segurança

| Controle | Implementação |
| --- | --- |
| Isolamento de tenant | Toda consulta vetorial carrega um filtro obrigatório de `tenant_id`; recuperação cross-tenant não é expressível pela camada de serviço |
| Remoção de segredos | Padrões de credenciais, tokens e PII são removidos durante a ingestão, antes do chunking e do embedding |
| Validação de upload | Allowlist de MIME no servidor (`.md`, `.txt`, `.pdf`); tipo é verificado no servidor, nunca confiado no cliente |
| CORS | Allowlist explícita de origens (apenas origens de desenvolvimento); sem wildcard |
| Tratamento de segredos | Todas as chaves em um `.env` ignorado pelo git; o arquivo env é resolvido por caminho absoluto para que o app não possa bootar silenciosamente com ambiente vazio |
| Respostas fundamentadas | A instrução do sistema proíbe responder fora do contexto recuperado; fontes acompanham cada resposta |
| Limites de API externa | Cache de embeddings, batch e backoff exponencial; `MAX_CHUNKS_PER_QUERY` limita tamanho de contexto e gasto |
| Auditabilidade | Citações expõem exatamente quais chunks fundamentaram cada resposta |

---

## 7. Recuperação: O Que É (e Não É)

- **É RAG de verdade.** Embeddings, busca vetorial, injeção de contexto e citação — não um
  bloco de prompt estático apresentado como recuperação.
- **Recuperação é semântica, não léxica.** A pergunta é embeddada com o mesmo modelo usado na
  ingestão; o ranking é similaridade vetorial, filtrada por tenant.
- **Overlap produz quase-duplicatas.** Chunking em janela deslizante significa que vários
  chunks de um documento podem rankear no top-5. A UI deduplica citações por
  `(filename, snippet)`; deduplicação no backend está no roadmap.
- **Não é fine-tuning e não é knowledge graph.** O modelo não tem memória dos documentos
  além do contexto injetado por requisição.
- **Idioma da resposta segue idioma do documento.** i18n cobre apenas a interface (§8).

---

## 8. Internacionalização

Três idiomas — PT-BR, EN, ZH-CN — com 26 chaves cada e sem biblioteca de i18n.

- Primeira visita detecta automaticamente via `navigator.language`.
- Um seletor dentro da interface sobrescreve a escolha e a persiste no `localStorage`.
- Cadeia de fallback: idioma ativo → inglês → chave crua (uma chave visível é um defeito
  detectável).
- `document.documentElement.lang` é atualizado na troca para acessibilidade e SEO.

Nota de escopo: i18n traduz a **UI**. Respostas do LLM dependem do idioma dos documentos
ingeridos.

---

## 9. Qualidade de Software

### 9.1 Estado atual: manual

QA é realizado **manualmente**. Não há suíte automatizada ainda; o roadmap para uma está no
§9.3. O checklist abaixo é executado em toda mudança:

| Verificação | Como é verificada |
| --- | --- |
| Caminho feliz de upload | Upload `.md` retorna um id de documento; logs de ingestão completam |
| MIME inválido rejeitado | Tipo fora do allowlist retorna erro de validação |
| Remoção | Um documento contendo um token falso é ingerido; o token está ausente dos chunks armazenados e das citações |
| Resposta fundamentada | Chat retorna resposta consistente com o runbook, mais fontes |
| Dedup de citações | Um corpus de documento único produz um bloco de citação, não cinco |
| Paridade de i18n | Seletor renderiza todas as strings da UI em PT, EN e ZH sem recarregar |
| CORS | Requisição de origem fora do allowlist é bloqueada pelo navegador |
| Recuperação de rate-limit | Um 429 durante ingestão se recupera via backoff sem perda de dados |
| Carregamento de settings | App sobe com `.env` na raiz do repositório independente do CWD do processo |
| Shutdown limpo | Parar com Ctrl+C não deixa porta ou lock do Qdrant segurados |

### 9.2 Log de incidentes (defeitos de desenvolvimento e falhas de processo)

Defeitos corrigidos silenciosamente não ensinam nada. Os incidentes abaixo são registrados
com causa raiz e guardrail. Itens 1–7 são defeitos de produto ou configuração; item 8 é um
incidente de ferramenta/processo, classificado separadamente porque nunca chegou ao produto.

| # | Sintoma | Causa raiz | Resolução e guardrail |
| --- | --- | --- | --- |
| 1 | Settings carregavam vazias (`ValidationError`, `input_value={}`) | `env_file = ".env"` no pydantic-settings resolve contra o CWD do processo; o arquivo foi movido para a raiz do repositório enquanto o servidor roda de `src/` | Arquivo env resolvido por caminho absoluto derivado da localização do módulo; verificação de boot-na-raiz adicionada ao QA manual |
| 2 | Servidor "inicia" mas nunca serve; boot trava | Um processo Python antigo segurava a porta 8000 e o lock de arquivo do Qdrant embutido depois que o terminal foi fechado sem Ctrl+C | Processos mortos; regra operacional adotada: sempre parar com Ctrl+C; Qdrant embutido documentado como single-process |
| 3 | Chamadas de embedding falhavam com HTTP 429 durante ingestão | Rate limits do tier gratuito do provedor | Backoff exponencial com retry, cache de embeddings em disco, embedding em batch; contexto limitado por `MAX_CHUNKS_PER_QUERY` |
| 4 | Editor e Vite reportavam opções de compilador desconhecidas (`erasableSyntaxOnly`, `noUncheckedSideEffectImports`, `tsBuildInfoFile` sem `incremental`) | O template do Vite emitia flags mais novas que a toolchain local de TypeScript | tsconfig set fixado em configuração conservadora e compatível com a toolchain |
| 5 | `npx tailwindcss init -p` falhou ("could not determine executable"); Markdown renderizava sem estilo | Falha de resolução de binário; `@tailwindcss/typography` ausente, então classes `prose` eram inertes | Arquivos de configuração escritos à mão; plugin typography adicionado depois que Markdown sem estilo foi observado |
| 6 | Requisições do frontend bloqueadas por CORS | Allowlist anterior à origem de dev do Vite (5173) | Allowlist atualizada com origens explícitas de dev; wildcard deliberadamente não usado |
| 7 | Mesmo documento citado até cinco vezes por resposta | Overlap em janela deslizante produz chunks quase-idênticos que todos rankeiam no top-5 | Dedup de citações na UI por `(filename, snippet)`; dedup no backend no roadmap |
| 8 | Incidente de processo: arquivos de código corrompidos com delimitadores de here-string do PowerShell; um módulo criado no diretório errado, quebrando resolução de imports | Here-strings interpolam backticks e `${}`; delimitadores foram parar dentro do conteúdo do arquivo; erro de colocação manual | Regra adotada: arquivos de código são criados apenas no editor, nunca via redirecionamento de shell; verificação pós-escrita (check de primeira/última linha). Classificado como falha de ferramenta/processo, não defeito de produto |

### 9.3 Roadmap de QA automatizado

- Suíte `pytest` para remoção, chunking, filtragem por tenant e validação de MIME.
- Vitest + Testing Library para componentes de frontend.
- GitHub Actions CI rodando a suíte em cada push.
- Verificação de paridade de i18n afirmando que todos os idiomas compartilham o mesmo conjunto de chaves.

---

## 10. Limites Honestos

- **Não implantado.** MVP local por decisão; estratégia de deploy está documentada, não
  executada (§13).
- **Sem autenticação ainda.** O tenant é um identificador fixo de desenvolvimento.
  Isolamento é forçado na camada de serviço, mas não há login; JWT é o primeiro item do
  roadmap. Esta instância não deve ser exposta a redes não confiáveis.
- **Qdrant embutido é single-process.** Inadequado para workers concorrentes ou escala
  horizontal; modo servidor é o caminho de produção.
- **QA apenas manual.** Não há suíte automatizada ainda (§9.3).
- **Modelos do tier gratuito** foram escolhidos por limite de custo, não liderança em
  benchmarks.
- **Dedup de citações acontece na UI.** O backend ainda pode devolver chunks redundantes.
- **Ingestão de PDF é aceita mas ainda não coberta pelo QA manual.** Markdown e texto puro
  são os caminhos verificados.

---

## 11. Estrutura do Projeto

```
lore-rag/
├── src/                      Backend FastAPI
│   ├── app/
│   │   ├── api/v1/           Routers: documents, ai/chat
│   │   ├── core/             Settings (pydantic-settings), constantes de segurança
│   │   ├── db/               Base e sessão do SQLAlchemy
│   │   ├── models/           Modelos relacionais
│   │   ├── services/         Ingestão, remoção, chunking, embedding,
│   │   │                     vector store, orquestração de RAG
│   │   └── main.py           App factory, CORS, lifespan
│   └── run.py                Entry point de desenvolvimento
├── front-end/                SPA React (Vite)
│   ├── src/
│   │   ├── components/       Chat, FileUpload, LanguageSwitcher
│   │   ├── i18n/             I18nContext + locales (pt-BR, en, zh-CN)
│   │   ├── services/api.ts   Cliente Axios
│   │   └── types/            Tipos TypeScript compartilhados
│   └── ...
├── .env                      Ignorado pelo git; nunca commitado
└── README.md / README.pt-BR.md / README.zh-CN.md
```

---

## Screenshots

### Interface principal

<p align="center">
  <img src="docs/screenshots/interface.png" alt="Lore main interface with upload and chat" width="800" />
</p>

<p align="center">
  <em>Upload de documentos e chat RAG com citações de fontes</em>
</p>

---

### Upload de documento

<p align="center">
  <img src="docs/screenshots/upload-success.png" alt="Document upload with success message" width="800" />
</p>

<p align="center">
  <em>Pipeline completo: validação MIME, sanitização, chunking e vetorização</em>
</p>

---

### Chat RAG com citações

<p align="center">
  <img src="docs/screenshots/chat-response.png" alt="Chat response with cited sources" width="800" />
</p>

<p align="center">
  <em>Resposta fundamentada em contexto recuperado, com chunks citados e deduplicados</em>
</p>

---

### Internacionalização

<p align="center">
  <img src="docs/screenshots/language-switcher.png" alt="Language switcher PT/EN/ZH" width="800" />
</p>

<p align="center">
  <em>Seletor de idioma com detecção automática e persistência em localStorage</em>
</p>

---

## 12. Como Rodar

### Pré-requisitos

- Python 3.11+, Node 18+, PostgreSQL rodando localmente
- Chaves de API: OpenRouter (embeddings), Groq (chat)

### Backend

```bash
cd src
python -m venv ../venv
../venv/Scripts/Activate.ps1        # Windows; use bin/activate no Unix
pip install -r requirements.txt
python run.py                       # http://127.0.0.1:8000  (Swagger em /docs)
```

### Frontend

```bash
cd front-end
npm install
npm run dev                         # http://localhost:5173
```

Ambos os processos devem rodar simultaneamente, cada um em seu próprio terminal. Pare-os
com Ctrl+C; fechar um terminal enquanto um processo roda pode deixar a porta ou o lock do
Qdrant segurados (§9.2, incidente 2).

### Variáveis de ambiente (`.env` na raiz do repositório, nunca commitado)

| Variável | Propósito |
| --- | --- |
| `DATABASE_URL` | String de conexão PostgreSQL |
| `OPENROUTER_API_KEY` | Provedor de embeddings |
| `GROQ_API_KEY` | Provedor do LLM de chat |
| `EMBEDDING_MODEL` / `DEFAULT_LLM_MODEL` | Identificadores de modelos |
| `QDRANT_PATH` | Diretório do vector store embutido |
| `MAX_CHUNKS_PER_QUERY` | Limite de recuperação (tamanho de contexto e gasto) |
| `RATE_LIMIT_PER_MINUTE` | Configuração de rate-limit da aplicação |
| `SECRET_KEY` | Segredo da aplicação |
| `APP_NAME` / `DEBUG` | Metadados e flag de debug |

---

## 13. Estado e Estratégia de Deploy

Não implantado, por decisão. Três estratégias foram avaliadas para uma futura execução de
produção:

| Estratégia | Forma | Trade-off |
| --- | --- | --- |
| VPS + Docker Compose | Containers para app, PostgreSQL e servidor Qdrant; dados em volumes | Custo mais baixo, controle total, demonstra containerização; você é responsável por backups |
| Totalmente gerenciado | PaaS para o app, Postgres gerenciado, Qdrant Cloud | Zero ops; custo maior, engenharia menos demonstrável |
| Híbrido | App em PaaS + Postgres gerenciado + Qdrant containerizado | Meio-termo; volumes de PaaS stateless são uma armadilha para dados vetoriais |

Mudanças necessárias para qualquer execução de produção: cliente Qdrant em modo duplo
(`QDRANT_URL` + `QDRANT_API_KEY` quando definidos, caminho embutido caso contrário);
`DATABASE_URL` apontando para instância gerenciada; autenticação JWT substituindo o tenant
de desenvolvimento; reverse proxy com HTTPS; rate-limit por usuário; política de backup e
monitoramento.

---

## 14. Roadmap

- Autenticação JWT (substituir o identificador de tenant de desenvolvimento)
- Suíte de testes automatizados e CI (§9.3)
- Deduplicação de citações no backend
- Docker Compose para desenvolvimento local (PostgreSQL + servidor Qdrant)
- Cobertura de QA manual para ingestão de PDF
- Execução de uma das estratégias de deploy (§13)

---

## 15. Licença e Autora

MIT. Veja `LICENSE`.

**Brenda Tavares** — Desenvolvedora Backend
Bacharelado em Humanidades, Universidade Federal da Bahia (UFBA)
Desenvolvimento Backend, Universidade Pitágoras Unopar Anhanguera
GitHub: https://github.com/Brenda-Tavares
LinkedIn: https://www.linkedin.com/in/brenda-campos-tavares/
Contato: tavaresbrenda@proton.me

Embeddings servidos por OpenRouter; inferência servida por Groq; vector store por Qdrant
(open source). Todas as chaves de provedores são fornecidas pelo chamador e nunca commitadas.