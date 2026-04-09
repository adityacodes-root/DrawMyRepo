output "instance_public_ip" {
  description = "The public IP of the web server"
  value       = aws_instance.app_server.public_ip
}

output "deployment_instructions" {
  value = <<EOT

The EC2 instance is spinning up! Because your project files are local, 
you will need to sync them to the server and start docker-compose.

Run these commands on your terminal:

1. Copy files to the server:
rsync -avz --exclude '.git' --exclude 'terraform' -e "ssh -o StrictHostKeyChecking=no" .. ubuntu@${aws_instance.app_server.public_ip}:/home/ubuntu/drawmyrepo/

2. SSH into the server and start the app:
ssh ubuntu@${aws_instance.app_server.public_ip} "cd /home/ubuntu/drawmyrepo && sudo docker-compose up -d"

3. Visit your live site:
http://${aws_instance.app_server.public_ip}
EOT
}
