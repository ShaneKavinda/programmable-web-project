import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { ApiErrorSnackbar } from "../components/ApiErrorSnackbar";
import { useAuth } from "../context/AuthContext";
import { getMyProfile, updateMyProfile } from "../services/auth";

const schema = z.object({
  firstname: z.string().min(1, "Required"),
  lastname: z.string().min(1, "Required"),
  email: z.string().email("Enter a valid email"),
});

type FormValues = z.infer<typeof schema>;

export const ProfilePage = () => {
  const { setAuth, token, user } = useAuth();
  const { control, handleSubmit, reset, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      firstname: "",
      lastname: "",
      email: "",
    },
  });

  const profileQuery = useQuery({
    queryKey: ["me", user?.id],
    queryFn: getMyProfile,
    enabled: Boolean(token),
  });

  useEffect(() => {
    if (profileQuery.data) {
      reset({
        firstname: profileQuery.data.firstname,
        lastname: profileQuery.data.lastname,
        email: profileQuery.data.email,
      });
    }
  }, [profileQuery.data, reset]);

  const mutation = useMutation({
    mutationFn: updateMyProfile,
    onSuccess: (updatedUser) => {
      if (token) {
        setAuth(token, updatedUser);
      }
    },
  });

  const pageError = profileQuery.error ?? mutation.error;

  return (
    <Card>
      <CardContent>
        <Stack spacing={2.5} maxWidth={600}>
          <ApiErrorSnackbar error={pageError} />
          <Typography variant="h5" fontWeight={700}>
            My Profile
          </Typography>
          {mutation.isSuccess && <Alert severity="success">Profile updated successfully.</Alert>}
          <Controller
            name="firstname"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                value={field.value ?? ""}
                label="First name"
                error={!!formState.errors.firstname}
                helperText={formState.errors.firstname?.message}
              />
            )}
          />
          <Controller
            name="lastname"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                value={field.value ?? ""}
                label="Last name"
                error={!!formState.errors.lastname}
                helperText={formState.errors.lastname?.message}
              />
            )}
          />
          <Controller
            name="email"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                value={field.value ?? ""}
                label="Email"
                type="email"
                autoComplete="email"
                error={!!formState.errors.email}
                helperText={formState.errors.email?.message}
              />
            )}
          />
          <Typography variant="body2" color="text.secondary">
            User ID: {user?.id}
          </Typography>
          <Button
            variant="contained"
            onClick={handleSubmit((values) => mutation.mutate(values))}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Updating..." : "Update profile"}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
};

