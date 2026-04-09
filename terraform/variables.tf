variable "aws_region" {
  description = "AWS region deployed to"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "Your AWS Access Key ID"
  type        = string
  sensitive   = true
}

variable "aws_secret_key" {
  description = "Your AWS Secret Access Key"
  type        = string
  sensitive   = true
}

variable "aws_session_token" {
  description = "Your AWS Session Token (only required if using temporary credentials)"
  type        = string
  sensitive   = true
  default     = null
}

variable "aws_key_name" {
  description = "The name of the existing AWS Key Pair (e.g. new1)"
  type        = string
  default     = "new1"
}
