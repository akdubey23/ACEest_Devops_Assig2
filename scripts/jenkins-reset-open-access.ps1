# Run ONCE in PowerShell as Administrator:
#   Right-click PowerShell -> Run as administrator
#   cd "C:\Users\Akanksha\OneDrive\Documents\Akanksha Documents\BITS P\3 Sem\DevOpsAssignment\scripts"
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\jenkins-reset-open-access.ps1
#
# Then open http://localhost:8081 (no login), go to Manage Jenkins -> Security,
# re-enable security, create user "admin" with a new password.

$ErrorActionPreference = "Stop"
$jhome = "C:\ProgramData\Jenkins\.jenkins"
$cfg = Join-Path $jhome "config.xml"

if (-not (Test-Path $cfg)) {
    Write-Error "Jenkins config not found: $cfg"
    exit 1
}

$backup = Join-Path $jhome ("config.xml.backup_{0:yyyyMMdd_HHmmss}" -f (Get-Date))
Copy-Item $cfg $backup -Force
Write-Host "Backed up to: $backup"

Stop-Service Jenkins -Force
Start-Sleep -Seconds 4

$xml = @'
<?xml version='1.1' encoding='UTF-8'?>
<hudson>
  <disabledAdministrativeMonitors/>
  <version>2.541.2</version>
  <numExecutors>2</numExecutors>
  <mode>NORMAL</mode>
  <useSecurity>false</useSecurity>
  <disableRememberMe>false</disableRememberMe>
  <projectNamingStrategy class="jenkins.model.ProjectNamingStrategy$DefaultProjectNamingStrategy"/>
  <workspaceDir>${JENKINS_HOME}/workspace/${ITEM_FULL_NAME}</workspaceDir>
  <buildsDir>${ITEM_ROOTDIR}/builds</buildsDir>
  <jdks/>
  <viewsTabBar class="hudson.views.DefaultViewsTabBar"/>
  <myViewsTabBar class="hudson.views.DefaultMyViewsTabBar"/>
  <clouds/>
  <scmCheckoutRetryCount>0</scmCheckoutRetryCount>
  <views>
    <hudson.model.AllView>
      <owner class="hudson" reference="../../.."/>
      <name>all</name>
      <filterExecutors>false</filterExecutors>
      <filterQueue>false</filterQueue>
      <properties class="hudson.model.View$PropertyList"/>
    </hudson.model.AllView>
  </views>
  <primaryView>all</primaryView>
  <slaveAgentPort>-1</slaveAgentPort>
  <label></label>
  <crumbIssuer class="hudson.security.csrf.DefaultCrumbIssuer">
    <excludeClientIPFromCrumb>false</excludeClientIPFromCrumb>
  </crumbIssuer>
  <nodeProperties/>
  <globalNodeProperties/>
  <nodeRenameMigrationNeeded>false</nodeRenameMigrationNeeded>
</hudson>
'@

[System.IO.File]::WriteAllText($cfg, $xml, [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote open-access config (useSecurity=false)."

Start-Service Jenkins
Start-Sleep -Seconds 6
Get-Service Jenkins
Write-Host "Done. Open Jenkins in the browser and re-enable security + create a new admin user."
